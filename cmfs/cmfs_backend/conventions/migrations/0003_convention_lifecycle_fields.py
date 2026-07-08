"""
FILE: cmfs/cmfs_backend/conventions/migrations/0003_convention_lifecycle_fields.py
ACTION: CREATE (Phase 3)

Adds lifecycle timestamp fields to Convention, and FK fields (county, region)
to ConventionUnit. Also adds unique_together constraint.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conventions', '0002_rls_and_triggers'),
    ]

    operations = [
        # ── Convention: lifecycle timestamps ─────────────────────────────────
        migrations.AddField(
            model_name='convention',
            name='scope_locked_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='convention',
            name='published_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='convention',
            name='started_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='convention',
            name='ended_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='convention',
            name='financially_closed_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='convention',
            name='archived_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='convention',
            name='financially_closed_by_id',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='convention',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # ── ConventionUnit: FK fields ─────────────────────────────────────────
        migrations.AddField(
            model_name='conventionunit',
            name='county',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='convention_units',
                to='conventions.county',
            ),
        ),
        migrations.AddField(
            model_name='conventionunit',
            name='region',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='convention_units',
                to='conventions.region',
            ),
        ),
        migrations.AddField(
            model_name='conventionunit',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),

        # ── ConventionUnit: unique_together ───────────────────────────────────
        migrations.AlterUniqueTogether(
            name='conventionunit',
            unique_together={('convention', 'scope_type', 'scope_id')},
        ),

        # ── RLS: scope lock trigger (DB-level enforcement) ────────────────────
        migrations.RunSQL(
            sql="""
            -- Trigger to prevent scope/fees from being changed once locked
            CREATE OR REPLACE FUNCTION enforce_convention_scope_lock()
            RETURNS TRIGGER AS $$
            BEGIN
                IF OLD.scope_locked = TRUE THEN
                    IF NEW.scope IS DISTINCT FROM OLD.scope THEN
                        RAISE EXCEPTION 'Convention scope is permanently locked and cannot be changed.';
                    END IF;
                    IF NEW.fee_student IS DISTINCT FROM OLD.fee_student
                        OR NEW.fee_kessat IS DISTINCT FROM OLD.fee_kessat
                        OR NEW.fee_associate IS DISTINCT FROM OLD.fee_associate
                    THEN
                        RAISE EXCEPTION 'Convention fees are permanently locked once published.';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS convention_scope_lock_trigger ON conventions;
            CREATE TRIGGER convention_scope_lock_trigger
                BEFORE UPDATE ON conventions
                FOR EACH ROW
                EXECUTE FUNCTION enforce_convention_scope_lock();

            -- Trigger to prevent convention_units from being modified once scope is locked
            CREATE OR REPLACE FUNCTION enforce_convention_unit_lock()
            RETURNS TRIGGER AS $$
            DECLARE
                v_scope_locked BOOLEAN;
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    SELECT scope_locked INTO v_scope_locked FROM conventions WHERE id = NEW.convention_id;
                ELSE
                    SELECT scope_locked INTO v_scope_locked FROM conventions WHERE id = OLD.convention_id;
                END IF;

                IF v_scope_locked = TRUE AND TG_OP IN ('INSERT', 'DELETE') THEN
                    RAISE EXCEPTION 'Convention unit structure is permanently locked once the convention is published.';
                END IF;

                RETURN COALESCE(NEW, OLD);
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS convention_unit_lock_trigger ON convention_units;
            CREATE TRIGGER convention_unit_lock_trigger
                BEFORE INSERT OR DELETE ON convention_units
                FOR EACH ROW
                EXECUTE FUNCTION enforce_convention_unit_lock();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS convention_scope_lock_trigger ON conventions;
            DROP FUNCTION IF EXISTS enforce_convention_scope_lock();
            DROP TRIGGER IF EXISTS convention_unit_lock_trigger ON convention_units;
            DROP FUNCTION IF EXISTS enforce_convention_unit_lock();
            """,
        ),
    ]
