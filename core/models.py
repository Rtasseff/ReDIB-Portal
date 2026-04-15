"""
Core models for ReDIB COA portal.
Includes: User, Organization, Node, Equipment, UserRole
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords


# ORCID iDs are sixteen digits in four groups of four separated by hyphens,
# with the final character allowed to be an X (the checksum). Example:
# 0000-0002-1825-0097
ORCID_VALIDATOR = RegexValidator(
    regex=r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$',
    message='ORCID iD must be in the format XXXX-XXXX-XXXX-XXXX '
            '(last character may be X).',
)

# Loose phone validator: digits, spaces, and common separators (+ - . ( ))
# only. Rejects alphabetic characters so typos like "+34 O00..." are caught.
PHONE_VALIDATOR = RegexValidator(
    regex=r'^[\d\s()+\-.]{5,}$',
    message='Phone numbers may contain only digits, spaces, and the '
            'characters + - . ( ).',
)


class Organization(models.Model):
    """Parent organizations (ministries, universities, companies)"""

    ORG_TYPES = [
        ('company', 'Company / Empresa'),
        ('university', 'University / Universidad'),
        ('other', 'Other / Otro'),
    ]

    name = models.CharField(max_length=255)
    vat = models.CharField(max_length=50, blank=True, help_text='VAT/NIF number')
    country = models.CharField(max_length=100, default='Spain')
    organization_type = models.CharField(max_length=50, choices=ORG_TYPES)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Organizations'

    def __str__(self):
        return self.name


class Node(models.Model):
    """ReDIB network nodes (4 nodes: CICbiomaGUNE, BioImaC, La Fe, CNIC)"""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text='Unique node identifier')
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    acknowledgment_text = models.TextField(
        help_text='Text to be included in publications using this node',
        blank=True
    )

    # Leadership
    # We may not want this as from the pov of the COA portal the director may not be relevant
    # A manager/adminstrator or coordinator role may be more appropriate
    director = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='directed_nodes',
        help_text='Node director/coordinator'
    )

    # Contact information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Equipment(models.Model):
    """Essential infrastructure at each node"""

    EQUIPMENT_CATEGORIES = [
        ('mri', 'MRI'),
        ('pet', 'PET'),
        ('ct', 'CT'),
        ('pet_ct', 'PET-CT'),
        ('pet_mri', 'PET-MRI'),
        ('spect_pet_ct', 'SPECT-PET-CT'),
        ('spect_pet_ct_oi', 'SPECT-PET-CT-OI'),
        ('cyclotron', 'Cyclotron'),
        ('spect', 'SPECT'),
        ('ultrasound', 'Ultrasound'),
        ('optical', 'Optical Imaging'),
        ('other', 'Other'),
    ]

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='equipment')
    name = models.CharField(max_length=100, help_text='e.g., MRI 7T, PET-CT')
    category = models.CharField(max_length=50, choices=EQUIPMENT_CATEGORIES)
    description = models.TextField(blank=True)
    technical_specs = models.TextField(blank=True, help_text='Technical specifications')

    is_essential = models.BooleanField(
        default=True,
        help_text='ICTS essential facility available for COA'
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['node', 'name']
        verbose_name_plural = 'Equipment'

    def __str__(self):
        return f"{self.node.code} - {self.name}"


class UserManager(BaseUserManager):
    """Custom manager for User model with email-based authentication."""

    def get_by_natural_key(self, email):
        """
        Retrieve user by email (natural key for email-based authentication).
        """
        return self.get(**{self.model.USERNAME_FIELD: email})

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular User with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)  # Set username to email for compatibility
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Extended user with roles and affiliations"""

    # Override username field to allow email-based authentication
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)

    # Use custom manager
    objects = UserManager()

    # Additional fields
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    orcid = models.CharField(
        max_length=20,
        blank=True,
        validators=[ORCID_VALIDATOR],
        help_text='ORCID iD in the format XXXX-XXXX-XXXX-XXXX'
    )
    phone = models.CharField(max_length=30, blank=True, validators=[PHONE_VALIDATOR])
    position = models.CharField(max_length=200, blank=True, help_text='Job title/position')

    # Consent
    auto_data_consent = models.BooleanField(
        default=False,
        help_text='Automatic data processing consent for all future applications'
    )

    # Email preferences
    receive_call_notifications = models.BooleanField(
        default=True,
        help_text='Receive notifications when new calls are published'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['email']

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    @property
    def is_profile_complete(self):
        """Check if all required profile fields are filled."""
        return all([
            self.first_name,
            self.last_name,
            self.phone,
            self.organization_id,
            self.position,
        ])


class UserRole(models.Model):
    """Role assignments (users can have multiple roles)"""

    ROLES = [
        ('applicant', 'Applicant'),
        ('node_coordinator', 'Node Coordinator'),
        ('evaluator', 'Evaluator'),
        ('coordinator', 'ReDIB Coordinator'),
        ('admin', 'Administrator'),
    ]

    AREAS = [
        ('', 'Not applicable'),
        ('clinical', 'Clinical'),
        ('preclinical', 'Preclinical'),
        ('radiochemistry', 'Radiochemistry'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLES)
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='For node-specific roles (node_coordinator)',
        related_name='staff'
    )
    areas = models.CharField(
        max_length=200,
        blank=True,
        help_text='Semicolon-separated specialization areas for evaluators (e.g. "clinical;preclinical")'
    )

    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['user', 'role']
        unique_together = ['user', 'role', 'node']
        verbose_name_plural = 'User Roles'

    def __str__(self):
        if self.node:
            return f"{self.user.email} - {self.get_role_display()} at {self.node.code}"
        return f"{self.user.email} - {self.get_role_display()}"

    @property
    def area_list(self):
        """Return areas as a list, e.g. ['clinical', 'preclinical']."""
        return [a.strip() for a in (self.areas or '').split(';') if a.strip()]

    def has_area(self, area):
        """Return True if this role covers the given specialization area."""
        return area in self.area_list
