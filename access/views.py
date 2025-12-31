"""
Views for the access app - Publication submission.
"""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .models import Publication
from .forms import PublicationForm


@login_required
def publication_list(request):
    """List user's submitted publications."""
    publications = Publication.objects.filter(
        application__applicant=request.user
    ).select_related('application').order_by('-reported_at')

    context = {
        'publications': publications,
    }
    return render(request, 'access/publication_list.html', context)


@login_required
def publication_submit(request):
    """Submit a new publication."""
    if request.method == 'POST':
        form = PublicationForm(request.POST, user=request.user)
        if form.is_valid():
            publication = form.save(commit=False)
            publication.reported_by = request.user
            publication.save()

            messages.success(request, f'Publication "{publication.title}" submitted successfully!')
            return redirect('access:publication_list')
    else:
        form = PublicationForm(user=request.user)

    context = {
        'form': form,
    }
    return render(request, 'access/publication_submit.html', context)
