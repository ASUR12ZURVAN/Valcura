from django.db import migrations


def create_missing_hospital_user_table(apps, schema_editor):
    hospital_user = apps.get_model('user_request', 'HospitalUser')
    table_names = schema_editor.connection.introspection.table_names()

    if hospital_user._meta.db_table not in table_names:
        schema_editor.create_model(hospital_user)


class Migration(migrations.Migration):

    dependencies = [
        ('user_request', '0001_initial'),
    ]

    run_before = [
        ('admin', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_missing_hospital_user_table,
            migrations.RunPython.noop,
        ),
    ]