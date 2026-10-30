"""Módulo `perfiles`: blueprint Flask de perfiles (roles) y matriz de permisos (RF-02). Capa: registro del módulo MVC."""

from app.core.module import make_blueprint

bp = make_blueprint(__name__)
