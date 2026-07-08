from django.db import migrations


class Migration(migrations.Migration):
    """
    Applies:
    1. RLS on delegates, payments, budget_expense_items, actual_expenses,
       write_offs, attendance, convention_units, audit_logs
    2. Scope-lock trigger on conventions table
    3. Audit log INSERT-only RLS policy
    """

    dependencies = [
        ('conventions', '0001_initial'),
        ('auth_app', '0001_initial'),
        ('budget', '0001_initial'),
        ('delegates', '0001_initial'),
        ('payments', '0001_initial'),
        ('gate', '0001_initial'),
        ('reports', '0001_initial'),
    ]

    operations = [

        # ── 1. Enable RLS on all protected tables ──────────────────────────
        migrations.RunSQL(
            sql="ALTER TABLE delegates ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE delegates DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE payments ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE payments DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE budget_expense_items ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE budget_expense_items DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE actual_expenses ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE actual_expenses DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE write_offs ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE write_offs DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE attendance DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE convention_units ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE convention_units DISABLE ROW LEVEL SECURITY;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;",
            reverse_sql="ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;",
        ),

        # ── 2. RLS policy — delegates (county isolation) ───────────────────
        migrations.RunSQL(
            sql="""
                CREATE POLICY county_isolation ON delegates
                    USING (
                        county_id = NULLIF(current_setting('app.current_county_id', true), '')::int
                        OR current_setting('app.bypass_rls', true) = 'on'
                    );
            """,
            reverse_sql="DROP POLICY IF EXISTS county_isolation ON delegates;",
        ),

        # ── 3. RLS policy — payments (via delegate → county) ───────────────
        migrations.RunSQL(
            sql="""
                CREATE POLICY county_isolation ON payments
                    USING (
                        delegate_id IN (
                            SELECT id FROM delegates
                            WHERE county_id = NULLIF(current_setting('app.current_county_id', true), '')::int
                        )
                        OR current_setting('app.bypass_rls', true) = 'on'
                    );
            """,
            reverse_sql="DROP POLICY IF EXISTS county_isolation ON payments;",
        ),

        # ── 4. RLS policy — budget_expense_items (via convention_unit) ─────
        migrations.RunSQL(
            sql="""
                CREATE POLICY county_isolation ON budget_expense_items
                    USING (
                        convention_unit_id IN (
                            SELECT id FROM convention_units
                            WHERE scope_type = 'county'
                              AND scope_id = NULLIF(current_setting('app.current_county_id', true), '')::int
                        )
                        OR current_setting('app.bypass_rls', true) = 'on'
                    );
            """,
            reverse_sql="DROP POLICY IF EXISTS county_isolation ON budget_expense_items;",
        ),

        # ── 5. RLS policy — actual_expenses (via budget_expense_item → unit) ─
        migrations.RunSQL(
            sql="""
                CREATE POLICY county_isolation ON actual_expenses
                    USING (
                        budget_expense_item_id IN (
                            SELECT bei.id FROM budget_expense_items bei
                            JOIN convention_units cu ON cu.id = bei.convention_unit_id
                            WHERE cu.scope_type = 'county'
                              AND cu.scope_id = NULLIF(current_setting('app.current_county_id', true), '')::int
                        )
                        OR current_setting('app.bypass_rls', true) = 'on'
                    );
            """,
            reverse_sql="DROP POLICY IF EXISTS county_isolation ON actual_expenses;",
        ),

        # ── 6. RLS policy — write_offs (via convention_unit) ──────────────
        migrations.RunSQL(
            sql="""
                CREATE POLICY county_isolation ON write_offs
                    USING (
                        convention_unit_id IN (
                            SELECT id FROM convention_units
                            WHERE scope_type = 'county'
                              AND scope_id = NULLIF(current_setting('app.current_county_id', true), '')::int
                        )
                        OR current_setting('app.bypass_rls', true) = 'on'
                    );
            """,
            reverse_sql="DROP POLICY IF EXISTS county_isolation ON write_offs;",
        ),

        # ── 7. RLS policy — attendance (via delegate → county) ─────────────
        migrations.RunSQL(
            sql="""
                CREATE POLICY county_isolation ON attendance
                    USING (
                        delegate_id IN (
                            SELECT id FROM delegates
                            WHERE county_id = NULLIF(current_setting('app.current_county_id', true), '')::int
                        )
                        OR current_setting('app.bypass_rls', true) = 'on'
                    );
            """,
            reverse_sql="DROP POLICY IF EXISTS county_isolation ON attendance;",
        ),

        # ── 8. RLS policy — convention_units (county scope filter) ─────────
        migrations.RunSQL(
            sql="""
                CREATE POLICY county_isolation ON convention_units
                    USING (
                        (scope_type = 'county'
                         AND scope_id = NULLIF(current_setting('app.current_county_id', true), '')::int)
                        OR scope_type IN ('regional', 'national')
                        OR current_setting('app.bypass_rls', true) = 'on'
                    );
            """,
            reverse_sql="DROP POLICY IF EXISTS county_isolation ON convention_units;",
        ),

        # ── 9. RLS policy — audit_logs (INSERT only, no UPDATE/DELETE) ─────
        migrations.RunSQL(
            sql="""
                CREATE POLICY audit_log_insert_only ON audit_logs
                    FOR INSERT WITH CHECK (true);
            """,
            reverse_sql="DROP POLICY IF EXISTS audit_log_insert_only ON audit_logs;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE POLICY audit_log_select ON audit_logs
                    FOR SELECT
                    USING (current_setting('app.bypass_rls', true) = 'on');
            """,
            reverse_sql="DROP POLICY IF EXISTS audit_log_select ON audit_logs;",
        ),

        # ── 10. Scope-lock trigger on conventions ──────────────────────────
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION enforce_scope_lock()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF OLD.scope_locked = TRUE THEN
                        IF NEW.scope IS DISTINCT FROM OLD.scope
                           OR NEW.fee_student IS DISTINCT FROM OLD.fee_student
                           OR NEW.fee_kessat IS DISTINCT FROM OLD.fee_kessat
                           OR NEW.fee_associate IS DISTINCT FROM OLD.fee_associate
                        THEN
                            RAISE EXCEPTION
                                'Convention scope and fees are permanently locked and cannot be changed.';
                        END IF;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS enforce_scope_lock();",
        ),
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER convention_scope_lock_trigger
                    BEFORE UPDATE ON conventions
                    FOR EACH ROW
                    EXECUTE FUNCTION enforce_scope_lock();
            """,
            reverse_sql="DROP TRIGGER IF EXISTS convention_scope_lock_trigger ON conventions;",
        ),
    ]