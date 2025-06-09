import time
import hashlib
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import CategoryRequest
from counts.models import ShopeeConta
from .serializers import CategoryRequestSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    request=CategoryRequestSerializer,
    responses=CategoryRequestSerializer,
    parameters=[
        OpenApiParameter('title', str, description='Título do produto para recomendação'),
        OpenApiParameter('bare', str, description='Token de usuário', required=True)
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
    base_string = f"{conta.partner_id}{path}{ts}"
    sign = hashlib.sha256((base_string + conta.partner_key).encode()).hexdigest()

    url = f"https://partner.test-stable.shopeemobile.com{path}"
    params = {
        "partner_id": conta.partner_id,
        "sign": sign,
        "timestamp": ts,
        "shop_id": conta.shop_id,
        "access_token": conta.access_token,
        "item_name": title,
    }

    try:
        resp = requests.get(url, params=params)
        data = resp.json()
    except Exception as e:
        return Response({'error': 'Erro na requisição à Shopee.', 'detalhes': str(e)}, status=500)

    category_id = None
    if resp.status_code == 200 and 'response' in data:
        category_id_list = data['response'].get('category_id')
        if isinstance(category_id_list, list) and category_id_list:
            category_id = category_id_list[0]

    req = CategoryRequest.objects.create(title=title, category_id=category_id)
    serializer = CategoryRequestSerializer(req)
    return Response(serializer.data)
