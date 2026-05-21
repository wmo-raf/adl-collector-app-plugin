from django import forms
from django.utils import timezone as dj_timezone


class SynopForm(forms.Form):
    observation_year = forms.ChoiceField(choices=[], label="Year")
    observation_month = forms.ChoiceField(choices=[
        (1, "January"),
        (2, "February"),
        (3, "March"),
        (4, "April"),
        (5, "May"),
        (6, "June"),
        (7, "July"),
        (8, "August"),
        (9, "September"),
        (10, "October"),
        (11, "November"),
        (12, "December"),
    ])
    raw_message = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "AAXX .."
        }),
        label="Raw SYNOP FM12 Message"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        now = dj_timezone.now().year
        
        years = [(y, y) for y in range(now - 20, now + 1)]
        
        self.fields["observation_year"].choices = years
        self.fields["observation_year"].initial = now
