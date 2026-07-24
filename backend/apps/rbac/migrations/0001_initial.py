import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=100, unique=True)),
                ('description', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='core.organization')),
            ],
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rbac.permission')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rbac.role')),
            ],
        ),
        migrations.AddField(
            model_name='role',
            name='permissions',
            field=models.ManyToManyField(related_name='roles', through='rbac.RolePermission', to='rbac.permission'),
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_assignments', to='rbac.role')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='role',
            unique_together={('org', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='rolepermission',
            unique_together={('role', 'permission')},
        ),
        migrations.AlterUniqueTogether(
            name='userrole',
            unique_together={('user', 'role')},
        ),
    ]
