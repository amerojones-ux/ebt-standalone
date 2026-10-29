"""Shared strict JSON decoding with exact decimal tokens."""
import json
from decimal import Decimal

def strict_json(text):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate JSON key: '+key)
            result[key]=value
        return result
    def invalid(value):raise ValueError('nonfinite JSON number: '+value)
    return json.loads(text,object_pairs_hook=unique,parse_constant=invalid,parse_float=Decimal)
