/* Component interaction checks in jsdom; this is not real-browser visual QA. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const ts=require('typescript'),{JSDOM}=require('jsdom'),React=require('react');
const {createRoot}=require('react-dom/client'),{act}=React;
const rootDir=path.resolve(__dirname,'..'),dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://localhost/en/checkout'});
Object.assign(global,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,localStorage:dom.window.localStorage,IS_REACT_ACT_ENVIRONMENT:true});
const original=Module._resolveFilename;
Module._resolveFilename=function(name,parent,...rest){if(name.startsWith('@shared/'))name=path.join(rootDir,'packages/ui',name.slice(8));if(name==='@i18n')name=path.join(rootDir,'packages/i18n/index.ts');return original.call(this,name,parent,...rest)};
const oldLoad=Module._load;Module._load=function(name,...args){if(name==='next/link')return {__esModule:true,default:({children,...props})=>React.createElement('a',props,children)};return oldLoad.call(this,name,...args)};
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,file)=>{const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText;module._compile(code,file)};
const Reports=require('../apps/admin/src/components/Reports.tsx').default;
const Checkout=require('../apps/storefront/src/components/Checkout.tsx').default;
const container=document.getElementById('root');let root=createRoot(container),errors=[],calls=[];
const run=async fn=>{try{await fn()}catch(e){errors.push(e)}};
const data={from:'2026-10-01',to:'2026-10-05',timezone:'Asia/Qatar',revenue:'120',sales:'100',orders:1,customers:1,refunds:'0',low_stock:0,qualified_sessions:2,conversion:'50',sales_by_date:[{date:'2026-10-01',sales:'100'}],sales_by_category:[],sales_by_brand:[],best_selling_products:[],conversion_provisional:true};
async function render(component,props){await act(async()=>{root.render(React.createElement(component,props))})}
async function change(node,value){await act(async()=>{const proto=node.tagName==='SELECT'?dom.window.HTMLSelectElement.prototype:dom.window.HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(node,value);node.dispatchEvent(new dom.window.Event('change',{bubbles:true}));node.dispatchEvent(new dom.window.Event('input',{bubbles:true}))})}
(async()=>{
 await render(Reports,{data,currency:'QAR',locale:'en',refresh:()=>{},busy:false});assert(container.textContent.includes('50.00%'));assert(container.textContent.includes('Sales over time'));
 await render(Reports,{data:{...data,conversion:null,sales_by_date:[]},currency:'QAR',locale:'ar',refresh:()=>{},busy:false});assert(container.textContent.includes('لا توجد مبيعات مقبولة'));
 await act(async()=>root.unmount());root=createRoot(container);
 global.fetch=async(url,options={})=>{const p=String(url).replace('/api/v1','');calls.push({p,options});let body;
 if(p==='/auth/csrf')body={csrfToken:'test-token'};
 else if(p==='/store/delivery-methods')body=[{id:'pickup',kind:'pickup',name:'Pickup',pickup_address:'Test pickup'}];
 else if(p==='/store/delivery-areas')body=[];
 else if(p==='/checkout/quote')body={id:'quote-1',expires_at:new Date(Date.now()+300000).toISOString(),gross:'100',discount:'0',delivery_fee:'0',total:'100'};
 else if(p==='/checkout/orders')body={id:'order-1',number:'TEST-1',state:'pending',payment_method:'card',total:'100',payment:{state:'pending',checkout_url:'https://pay.example.invalid/checkout'}};
 else throw new Error('Unexpected route '+p);
 return new Response(JSON.stringify(body),{status:p==='/checkout/orders'?201:200,headers:{'Content-Type':'application/json'}});
 };
 const props={cfg:{currency:'QAR',cod_enabled:true,bank_enabled:true,card_enabled:true},locale:'en',bag:{items:[{id:'i',name:'Test product',quantity:1,price:'100'}],version:1},setBag:()=>{},run,busy:false,user:null};
 await render(Checkout,props);assert(container.textContent.includes('Credit / debit card'));
 const selects=container.querySelectorAll('select');await change(selects[0],'pickup');await change(container.querySelector('select[aria-label="Payment method"]'),'card');
 const quoteButton=[...container.querySelectorAll('button')].find(b=>b.textContent==='Calculate total');assert(!quoteButton.disabled);await act(async()=>quoteButton.click());
 assert(container.textContent.includes('100.00'));
 await act(async()=>container.querySelector('form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));
 assert(container.textContent.includes('Your order is awaiting payment'));assert.equal(container.querySelector('a[href="https://pay.example.invalid/checkout"]').textContent,'Continue to secure card payment');
 const placed=calls.find(c=>c.p==='/checkout/orders');assert.equal(placed.options.headers.get('Idempotency-Key'),'quote-1');assert.equal(JSON.parse(placed.options.body).payment_method,'card');assert.equal(errors.length,0);
 await act(async()=>root.unmount());root=createRoot(container);await render(Checkout,{...props,cfg:{...props.cfg,card_enabled:false},locale:'ar'});assert(!container.textContent.includes('بطاقة ائتمان'));assert(container.textContent.includes('طريقة الدفع'));

 await act(async()=>root.unmount());root=createRoot(container);
 const Admin=require('../apps/admin/src/app/page.tsx').default;
 global.fetch=async(url)=>{const p=String(url).replace('/api/v1','');let body;
 if(p==='/store/config')body={business_name:'Test retailer',currency:'QAR',primary_color:'#1c5948'};
 else if(p==='/auth/session')body={id:'staff-1',email:'staff@example.invalid',staff:true,staff_mfa:true,capabilities:['catalog.view']};
 else if(p==='/admin/resources')body=[{name:'products',fields:[{name:'name',type:'CharField'}],writable:false}];
 else if(p==='/admin/products?page=1')body={results:[{id:'p1',name:'Read-only product',status:'active'}],next:null};
 else throw new Error('Unexpected admin route '+p);
 return new Response(JSON.stringify(body),{status:200});
 };
 await render(Admin,{});assert(container.textContent.includes('Read-only product'));assert(![...container.querySelectorAll('button')].some(b=>b.textContent==='Create'||b.textContent==='Edit'));
 await act(async()=>[...container.querySelectorAll('button')].find(b=>b.textContent==='العربية').click());assert.equal(document.documentElement.dir,'rtl');assert(container.textContent.includes('المنتجات'));
 await act(async()=>root.unmount());dom.window.close();console.log('PASS: report contract, Arabic empty state, checkout quote, card handoff, idempotency key, disabled gateway visibility and read-only admin navigation (jsdom).');

})().catch(e=>{console.error(e);process.exitCode=1;dom.window.close()});
