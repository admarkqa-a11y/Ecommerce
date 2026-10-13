from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError

class ObjectJSONParser(JSONParser):
    def parse(self,stream,media_type=None,parser_context=None):
        result=super().parse(stream,media_type,parser_context)
        if not isinstance(result,dict):raise ParseError('The JSON request body must be an object.')
        return result
