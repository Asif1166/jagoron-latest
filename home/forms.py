from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'placeholder': 'আপনার মন্তব্য লিখুন...', 
                'class': 'form-control',
                'rows': 3
            }),
        }
