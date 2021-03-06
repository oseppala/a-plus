# Django
from django import forms
from django.utils.translation import ugettext_lazy as _

# A+
from exercise.submission_models import Submission
from exercise.exercise_models import BaseExercise
from userprofile.models import UserProfile


class SubmissionReviewForm(forms.Form):
    points = forms.IntegerField(min_value=0,
                                help_text=_("Possible penalties are not "
                                            "applied - the points are set "
                                            "as given."))
    feedback = forms.CharField(required=False,
                               widget=forms.Textarea,
                               help_text=_("HTML formatting is allowed"))

    def __init__(self, *args, **kwargs):
        self.exercise = kwargs.pop('exercise')
        super(SubmissionReviewForm, self).__init__(*args, **kwargs)

    def clean(self):
        points = self.cleaned_data.get("points")
        max_points = self.exercise.max_points

        if points > max_points:
            raise forms.ValidationError(_("The maximum points for this "
                                          "exercise is %d and the given "
                                          "points is more than that.")
                                        % self.exercise.max_points)

        return self.cleaned_data


class SubmissionCallbackForm(forms.Form):
    points          = forms.IntegerField(min_value=0)
    max_points      = forms.IntegerField(min_value=0)
    
    feedback        = forms.CharField(required=False)
    grading_payload = forms.CharField(required=False)
    error           = forms.BooleanField(required=False)
    
    def clean(self):
        points      = self.cleaned_data.get("points")
        max_points  = self.cleaned_data.get("max_points")

        if points and max_points:
            if points > max_points:
                raise forms.ValidationError("Points greater than maximum points are not allowed.")
        
            if points < 0:
                raise forms.ValidationError("Points lower than zero are not allowed.")
        
        return self.cleaned_data


class BaseExerciseForm(forms.ModelForm):
    class Meta:
        model = BaseExercise
        exclude = ("order", "course_module")
    
    def get_fieldsets(self):
        return [{"legend": _("Exercise"), "fields": self.get_exercise_fields()},
                {"legend": _("Grading"), "fields": self.get_grading_fields()},
                {"legend": _("Groups"), "fields": self.get_group_fields()},
                ]
    
    def get_exercise_fields(self):
        return (self["name"], 
                self["description"],
                self["category"])
    
    def get_grading_fields(self):
        return (self["max_submissions"],
                self["max_points"],
                self["points_to_pass"],
                self["allow_assistant_grading"])
    
    def get_group_fields(self):
        return (self["min_group_size"],
                self["max_group_size"])


# TODO: Rename to CreateAndAssessSubmissionForm
class StaffSubmissionForStudentForm(SubmissionReviewForm):
    """
    The queryset for the students field should be given dynamically when
    constructing the form by giving students_choices as a keyword argument.

    This form includes the submission_time which is in this case is interpreted
    as, the time when the student actually submitted the exercise to the course
    staff.
    """
    submission_time = forms.DateTimeField()
    # TODO: blank = True didn't work. What to do?
    students = forms.ModelMultipleChoiceField(queryset=UserProfile
                                              .objects.none(),
                                              required=False)
    students_by_student_id = forms.TypedMultipleChoiceField(
        empty_value=UserProfile.objects.none(),
        coerce=lambda student_id: UserProfile.get_by_student_id(student_id),
        choices=[(p.student_id, p.student_id) for p in UserProfile.objects.none()],
        required=False)

    def __init__(self, *args, **kwargs):
        super(StaffSubmissionForStudentForm, self).__init__(*args, **kwargs)
        self.fields["students"] = forms.ModelMultipleChoiceField(
            queryset=self.exercise.course_instance.get_students(),
            required=False)
        self.fields["students_by_student_id"] = forms.TypedMultipleChoiceField(
            empty_value=UserProfile.objects.none(),
            coerce=lambda student_id: UserProfile.get_by_student_id(student_id),
            choices=[(p.student_id, p.student_id) for p in self.exercise.course_instance.get_students().exclude(student_id=None)],
            required=False)

    def clean(self):
        self.cleaned_data = super(StaffSubmissionForStudentForm, self).clean()

        if not (self.cleaned_data.get("students") or self.cleaned_data.get("students_by_student_id")):
            raise forms.ValidationError(_("Both students and students_by_"
                                          "student_id must not be blank."))

        if self.cleaned_data.get("students") and self.cleaned_data.get("students_by_student_id"):
            raise forms.ValidationError(_("Use tudents or students_by_"
                                          "student_id but not both"))

        """
        if not self.exercise.is_submission_allowed(
                self.cleaned_data.get("students")):
            raise forms.ValidationError(_("Submission not allowed due to one "
                                          "or more of the submission "
                                          "constraints (eg. max submission, "
                                          "deadline)."))
        """

        return self.cleaned_data


class TeacherCreateAndAssessSubmissionForm(StaffSubmissionForStudentForm):
    """
    This form is a subclass of CrateAndAssessSubmissionForm with a field for
    giving also the grader.
    """
    grader = forms.ModelChoiceField(queryset=UserProfile
                                    .objects.none())

    def __init__(self, *args, **kwargs):
        super(TeacherCreateAndAssessSubmissionForm, self).__init__(*args,
                                                                   **kwargs)
        self.fields["grader"] = forms.ModelChoiceField(
            queryset=self.exercise.course_instance.get_course_staff())