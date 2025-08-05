import time
import hashlib
import hmac
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import CategoryRequest
from counts.models import ShopeeConta
from .serializers import CategoryRequestSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter

# Cache das categorias indexado por shop_id
CATEGORY_CACHE_TIMEOUT = getattr(settings, 'SHOPEE_CATEGORY_CACHE_TIMEOUT', 24 * 60 * 60)

# Função genérica com tenacity para retry em 429
@retry(
    retry=retry_if_exception_type(requests.HTTPError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8)
)
def shopee_get_with_retry(url, params):
    resp = requests.get(url, params=params)
    if resp.status_code == 429:
        # Forçar exceção para ativar retry
        http_err = requests.HTTPError(f"429 Too Many Requests for URL: {url}")
        raise http_err
    return resp

class CategoryCache:
    """Classe para gerenciar cache das categorias da Shopee"""
    
    @staticmethod
    def get_cache_key(shop_id, language='pt-br'):
        return f"shopee_categories_{shop_id}_{language}"
    
    @staticmethod
    def get_categories_from_api(conta, language='pt-br'):
        ts = int(time.time())
        path = "/api/v2/product/get_category"
        base_string = f"{conta.partner_id}{path}{ts}{conta.access_token}{conta.shop_id}"
        sign = hmac.new(conta.partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
        url = f"https://partner.shopeemobile.com{path}"
        params = {
            "partner_id": conta.partner_id,
            "sign": sign,
            "timestamp": ts,
            "shop_id": conta.shop_id,
            "access_token": conta.access_token,
            "language": language,
        }
        resp = shopee_get_with_retry(url, params)
        data = resp.json()
        if resp.status_code == 200 and 'response' in data:
            return data['response'].get('category_list', [])
        return []
    
    @staticmethod
    def get_categories_indexed(conta, language='pt-br', force_refresh=False):
        cache_key = CategoryCache.get_cache_key(conta.shop_id, language)
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        categories_list = CategoryCache.get_categories_from_api(conta, language)
        indexed = {}
        for cat in categories_list:
            cid = cat.get('category_id')
            if cid:
                indexed[cid] = {
                    'category_id': cid,
                    'display_name': cat.get('display_category_name', 'N/A'),
                    'original_name': cat.get('original_category_name', 'N/A'),
                    'parent_id': cat.get('parent_category_id'),
                    'has_children': cat.get('has_children', False)
                }
        cache.set(cache_key, indexed, CATEGORY_CACHE_TIMEOUT)
        return indexed

    @staticmethod
    def get_categories_by_ids(conta, category_ids, language='pt-br'):
        indexed = CategoryCache.get_categories_indexed(conta, language)
        return [indexed[cid] for cid in category_ids if cid in indexed]

@extend_schema(
    request=CategoryRequestSerializer,
    responses=CategoryRequestSerializer,
    parameters=[
        OpenApiParameter('title', str, description='Título do produto para recomendação'),
        OpenApiParameter('conta_id', int, description='ID da conta Shopee', required=True)
    ]
)
@api_view(['POST'])
def recommend_category(request):
    title = request.data.get('title')
    conta_id = request.data.get('conta_id')
    if not title or not conta_id:
        return Response({'error': 'Parâmetros "title" e "conta_id" são obrigatórios.'}, status=400)
    conta = ShopeeConta.objects.filter(id=conta_id).first()
    if not conta:
        return Response({'error': 'Conta Shopee não encontrada.'}, status=404)
    ts = int(time.time())
    path = "/api/v2/product/category_recommend"
    base_string = f"{conta.partner_id}{path}{ts}{conta.access_token}{conta.shop_id}"
    sign = hmac.new(conta.partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
    url = f"https://partner.shopeemobile.com{path}"
    params = {
        "partner_id": conta.partner_id,
        "sign": sign,
        "timestamp": ts,
        "shop_id": conta.shop_id,
        "access_token": conta.access_token,
        "item_name": title,
    }
    resp = shopee_get_with_retry(url, params)
    data = resp.json()
    category_id = None
    details = []
    if resp.status_code == 200 and 'response' in data:
        ids = data['response'].get('category_id', [])
        if ids:
            category_id = ids[0]
            details = CategoryCache.get_categories_by_ids(conta, ids)
    req = CategoryRequest.objects.create(title=title, category_id=category_id)
    serializer = CategoryRequestSerializer(req)
    result = serializer.data
    result['recommended_categories'] = details
    return Response(result)
