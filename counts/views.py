from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from category.models import CategoryRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

@login_required
def home(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        if title:
            CategoryRequest.objects.create(title=title)
            return redirect('home')
    itens = CategoryRequest.objects.all().order_by('-requested_at')
    return render(request, 'home.html', {'itens': itens})


@require_POST
@login_required
def excluir_titulo(request, id):
    item = get_object_or_404(CategoryRequest, id=id)
    item.delete()
    return redirect('home')
