"""Regression tests for backend review findings, without frontend dependencies."""
import csv
import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient
from apps.catalog.models import Product, Variant, Attribute, AttributeOption
from apps.catalog.services import create_variant
from apps.identity.models import User, Role
from apps.imports.services import upload, validate, confirm
from apps.inventory.models import Balance, Movement
from apps.orders.services import transition
from apps.payments.services import record_capture
from common.api import Conflict
from test_commerce import setup, checkout

pytestmark=pytest.mark.django_db


def file_for(rows):
    stream=io.StringIO()
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return SimpleUploadedFile('products.csv',stream.getvalue().encode())


def row(**changes):
    return dict(product_code='new',product_type='simple',name_en='New',name_ar='جديد',
                sku='NEW',category_code='general',price='20',stock='3',**changes)


def staff_client(user):
    client=APIClient();client.force_login(user)
    session=client.session;session['staff_mfa']=True;session.save()
    return client


@pytest.mark.parametrize('quantity',[True,1.5,'1.5',None,{},-1])
def test_cart_rejects_non_whole_quantities(setup,quantity):
    _,_,variant,_,_=setup
    response=APIClient().post('/api/v1/cart',{'variant_id':str(variant.id),'quantity':quantity},format='json')
    assert response.status_code==400


def test_import_preview_does_not_write_catalog_or_movements(setup):
    *_,admin=setup
    before=(Product.objects.count(),Variant.objects.count(),Balance.objects.count(),Movement.objects.count())
    job=upload(admin,file_for([row()]))
    assert job.state=='previewed',job.errors
    assert before==(Product.objects.count(),Variant.objects.count(),Balance.objects.count(),Movement.objects.count())
    confirm(job.id,job.plan_hash,admin)
    assert Variant.objects.get(sku='NEW').inventory.on_hand==3


@pytest.mark.parametrize('changes',[{'barcode':'SKU-1'}, {'low_stock_threshold':'-1'}, {'status':'unknown'}, {'name_ar':'','status':'active'}])
def test_import_validation_catches_commit_failures(setup,changes):
    _,_,variant,_,admin=setup
    variant.barcode='SKU-1';variant.save()
    data=row();data.update(changes)
    job=upload(admin,file_for([data]))
    assert job.state=='invalid'
    assert not Product.objects.filter(code='new').exists()
    with pytest.raises(Conflict):confirm(job.id,job.plan_hash,admin)


@pytest.mark.parametrize('header',['product_code,product_code','product_code,unexpected'])
def test_csv_rejects_ambiguous_headers(setup,header):
    *_,admin=setup
    with pytest.raises(ValidationError):upload(admin,SimpleUploadedFile('bad.csv',(header+'\na,b\n').encode()))


def test_cost_permission_rechecked_and_import_rows_not_leaked(setup):
    *_,admin=setup
    role=Role.objects.create(code='importer',name='Importer',capabilities=['imports.manage','catalog.cost'])
    actor=User.objects.create_user(username='importer',email='importer@example.invalid',is_staff=True)
    actor.roles.add(role)
    job=upload(actor,file_for([row(cost_price='12.34')]))
    role.capabilities=['imports.manage'];role.save()
    with pytest.raises(PermissionDenied):confirm(job.id,job.plan_hash,actor)
    client=staff_client(actor)
    assert client.get(f'/api/v1/admin/imports/{job.id}').status_code==403
    response=client.get('/api/v1/admin/imports')
    assert response.status_code==200 and 'cost_price' not in str(response.data) and '12.34' not in str(response.data)
    assert not Product.objects.filter(code='new').exists()


def test_committed_job_cannot_be_revalidated_or_confirmed_with_different_hash(setup):
    *_,admin=setup
    job=upload(admin,file_for([row()]));confirm(job.id,job.plan_hash,admin)
    with pytest.raises(Conflict):validate(job)
    with pytest.raises(Conflict):confirm(job.id,'wrong-hash',admin)
    assert Variant.objects.filter(sku='NEW').count()==1


def test_error_export_is_available_to_authorized_importer(setup):
    *_,admin=setup
    data=row();data['stock']='-1';job=upload(admin,file_for([data]))
    response=staff_client(admin).get(f'/api/v1/admin/imports/{job.id}/errors')
    assert response.status_code==200 and response['Content-Type'].startswith('text/csv')
    assert b'INVALID_ROW' in response.content


def test_expiry_worker_does_not_cancel_newly_paid_order(setup):
    cfg,_,variant,method,admin=setup;cfg.bank_enabled=True;cfg.save()
    order,_=checkout(APIClient(),variant,method,payment='bank')
    order.expires_at=timezone.now()-timedelta(minutes=1);order.save()
    record_capture(order.id,'bank-cleared','bank-capture',admin)
    transition(order.id,'cancel',reason='stale expiry scan',only_if_expired=True)
    order.refresh_from_db()
    assert order.state=='processing' and order.payment_state=='paid'
    assert Balance.objects.get(variant=variant).committed==2


def test_variant_axis_cannot_expand_silently(setup):
    _,product,_,_,_=setup
    variable=Product.objects.create(code='variable',name='Variable',category=product.category,kind='variable')
    for code in ['color','size']:
        attr=Attribute.objects.create(code=code,name=code,data_type='single_select',variant_eligible=True)
        AttributeOption.objects.create(attribute=attr,code='one',label='One')
    create_variant(variable,'V1','10',{'color':'one'})
    with pytest.raises(Exception):create_variant(variable,'V2','10',{'color':'one','size':'one'})
    assert variable.axes.count()==1 and variable.variants.count()==1


def test_readiness_reports_failure_without_internal_details():
    client=APIClient()
    assert client.get('/api/v1/health/live').status_code==200
    assert client.get('/api/v1/health/ready').status_code==200
    with patch('config.health.cache.get',side_effect=RuntimeError('private connection string')):
        response=client.get('/api/v1/health/ready')
    assert response.status_code==503 and b'private connection string' not in response.content


def test_resource_schema_uses_distinct_model_components():
    from drf_spectacular.generators import SchemaGenerator
    schema=SchemaGenerator().get_schema(public=True)
    components=schema['components']['schemas']
    assert 'sku' in components['VariantResource']['properties']
    assert 'parent' in components['CategoryResource']['properties']
    assert '/api/v1/checkout/orders' in schema['paths']
