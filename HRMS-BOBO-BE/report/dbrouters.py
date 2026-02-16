from hrms import settings


class ReportDBRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label in settings.SECOND_DB_APPS:  # your model name as in settings.py/DATABASES
            return 'report'
        return None

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the auth or contenttypes apps is
        involved.
        """
        if (
                obj1._meta.app_label in settings.SECOND_DB_APPS
                or obj2._meta.app_label in settings.SECOND_DB_APPS
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the auth and contenttypes apps only appear in the
        'auth_db' database.
        """
        if app_label in settings.SECOND_DB_APPS:
            return db == "report"
        return None
