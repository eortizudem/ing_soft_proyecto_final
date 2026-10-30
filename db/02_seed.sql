-- Archivo 02 de db/*.sql: datos base de LibriGest (catalogos, politicas, libros demo, asistente).
-- Se aplica despues de 01_schema.sql. Los usuarios (con hashes de contrasena) NO estan aqui: los siembra
-- app/seed.py (python -m app.seed). scripts/recrear_db.py --sin-semilla omite este archivo.

-- Roles
INSERT INTO rol(nombre, descripcion) VALUES
  ('admin','Administrador'),('catalogo','Catálogo'),('bibliotecario','Bibliotecario'),
  ('comprador','Comprador'),('alumno','Alumno'),('docente','Docente'),('visitante','Visitante'),
  ('colaborador','Colaborador');  -- D-12: personal de apoyo (catalogo + compras), sin préstamos

-- Permisos (modulos/funciones habilitables)
INSERT INTO permiso(nombre, descripcion) VALUES
  ('inicio','Pantalla de inicio'),('usuarios','Administración de usuarios'),
  ('perfiles','Perfiles y permisos'),('catalogo','Gestión del catálogo'),
  ('compras','Solicitudes de compra'),('reportes','Reportes'),
  ('buscar','Búsqueda de libros'),('diseno','Personalización visual'),
  ('guia','Guía de uso'),('funciones','Funciones del sistema'),
  ('prestamos','Préstamos, renovaciones y devoluciones'),('espera','Lista de espera'),
  ('adeudos','Multas, pagos, pérdida y daño'),('asistente','Asistente virtual'),
  ('notificaciones','Avisos enviados a los usuarios');

-- Matriz rol x permiso: cada rol recibe su lista; visitante/alumno/docente comparten el ELSE (basico)
INSERT INTO rol_permiso(id_rol, id_permiso, habilitado)
SELECT r.id_rol, p.id_permiso,
  p.nombre = ANY(CASE r.nombre
    WHEN 'admin' THEN ARRAY['inicio','usuarios','perfiles','catalogo','compras','reportes','buscar','diseno','guia','funciones',
                            'prestamos','espera','adeudos','asistente','notificaciones']
    WHEN 'catalogo' THEN ARRAY['inicio','catalogo','reportes','buscar','asistente','diseno','guia','funciones']
    WHEN 'bibliotecario' THEN ARRAY['inicio','catalogo','reportes','buscar','prestamos','espera','adeudos','asistente',
                                    'notificaciones','diseno','guia','funciones']
    WHEN 'comprador' THEN ARRAY['inicio','compras','buscar','asistente','diseno','guia','funciones']
    WHEN 'colaborador' THEN ARRAY['inicio','catalogo','compras','reportes','buscar','asistente','diseno','guia','funciones']
    ELSE ARRAY['inicio','buscar','asistente','diseno','guia','funciones'] END)
FROM rol r CROSS JOIN permiso p;

-- Ubicaciones fisicas de los libros demo (los libros demo usan la primera)
INSERT INTO ubicacion(planta, pasillo, librero, nivel) VALUES
  ('Planta baja','A','03',2),('Planta baja','B','05',1),('Planta alta','C','08',3);

-- Libros demo (LIB001..LIB007): uno de prestamo, consulta interna y un reservado (D-20)
INSERT INTO libro(clave,titulo,autor,editorial,tema,anio_publicacion,tipo_uso,clasificacion,sinopsis,precio_referencia,id_ubicacion,estado)
SELECT v.clave, v.titulo, v.autor, v.editorial, v.tema, v.anio, v.tipo, v.clasif, v.sinopsis, v.precio,
       (SELECT id_ubicacion FROM ubicacion WHERE planta='Planta baja' AND pasillo='A' AND librero='03' AND nivel=2),
       'activo'
FROM (VALUES
 ('LIB001','Ingeniería de software','Ian Sommerville','Pearson','Ingeniería de software',2011,'prestamo_externo','005.1 SOM',
  'Principios y técnicas para construir software mantenible. Incluye procesos, requisitos, arquitectura, diseño, pruebas y casos de aplicación.',850.00),
 ('LIB002','Clean Code','Robert C. Martin','Edición de biblioteca','Programación',2008,'prestamo_externo','005.1 MAR',
  'Obra de consulta de la colección académica y literaria de la Universidad Ducky.',800.00),
 ('LIB003','Pedro Páramo','Juan Rulfo','Edición de biblioteca','Literatura',1955,'consulta_interna','863 RUL',
  'Obra de consulta de la colección académica y literaria de la Universidad Ducky.',800.00),
 ('LIB004','Cálculo de una variable','James Stewart','Edición de biblioteca','Matemáticas',2012,'prestamo_externo','515 STE',
  'Obra de consulta de la colección académica y literaria de la Universidad Ducky.',800.00),
 ('LIB005','Redes de computadoras','Andrew S. Tanenbaum','Edición de biblioteca','Redes',2012,'prestamo_externo','004.6 TAN',
  'Obra de consulta de la colección académica y literaria de la Universidad Ducky.',800.00),
 ('LIB006','El principito','Antoine de Saint-Exupéry','Edición de biblioteca','Literatura',1943,'consulta_interna','843 SAI',
  'Obra de consulta de la colección académica y literaria de la Universidad Ducky.',800.00),
 ('LIB007','Álgebra lineal (bibliografía de cátedra)','Stanley I. Grossman','Edición de biblioteca','Matemáticas',2012,'reservado','512.5 GRO',
  'Libro reservado de la bibliografía de cátedra: se consulta en mostrador y no se presta.',800.00)
) AS v(clave,titulo,autor,editorial,tema,anio,tipo,clasif,sinopsis,precio);

-- Ejemplares: numero de copias por libro segun la tabla (clave, n)
INSERT INTO ejemplar(id_libro, numero_copia, estado, fecha_alta)
SELECT l.id_libro, g, 'disponible', CURRENT_DATE
FROM libro l JOIN (VALUES ('LIB001',5),('LIB002',3),('LIB003',2),('LIB004',4),('LIB005',2),('LIB006',1),('LIB007',1)) s(clave,n)
  ON s.clave = l.clave, generate_series(1, s.n) g;

-- Políticas (decisiones D-01..D-05): alumno 5 días hábiles / 2 libros / 2 renovaciones; docente 10 / 3 / 3; $10 MXN por día hábil.
-- Solo alumno y docente prestan (activa); los demás roles conservan una fila inactiva de referencia.
INSERT INTO politica_prestamo(id_rol, dias_prestamo, max_libros, max_renovaciones, multa_diaria, activa)
SELECT r.id_rol, v.dias, v.max_libros, v.renov, 10.00, v.activa
FROM rol r JOIN (VALUES ('admin',5,2,2,false),('catalogo',5,2,2,false),('bibliotecario',5,2,2,false),
  ('comprador',5,2,2,false),('colaborador',5,2,2,false),('alumno',5,2,2,true),('docente',10,3,3,true)
  ) v(rol,dias,max_libros,renov,activa) ON v.rol = r.nombre;

-- Intenciones que reconoce el asistente virtual (S3)
INSERT INTO intencion(nombre, descripcion) VALUES
  ('saludo','El usuario saluda al asistente'),
  ('buscar_libro','Consulta de disponibilidad o búsqueda de libros'),
  ('horarios','Horarios y servicios de la biblioteca'),
  ('prestamo','Reglas de préstamo de libros'),
  ('renovacion','Renovación de préstamos'),
  ('multas','Multas y adeudos'),
  ('recuperar_contrasena','Recuperación de contraseña'),
  ('solicitar_compra','Solicitud de adquisición de libros'),
  ('despedida','El usuario se despide'),
  ('ayuda','El usuario pregunta qué puede hacer el asistente'),
  ('reglas','Explicación de las reglas de préstamo, renovación y multas'),
  ('ubicacion','Dónde está un libro o la biblioteca'),
  ('estatus_prestamos','Consulta de los préstamos propios (requiere sesión)'),
  ('estatus_multas','Consulta de los adeudos propios (requiere sesión)'),
  ('pasar_a_bibliotecario','El usuario pide hablar con un bibliotecario'),
  ('no_entendido','El asistente no reconoció el tema de la pregunta');

-- FAQ alineadas a politica_prestamo (el asistente debe preferir leer la política; estos textos son el respaldo).
INSERT INTO pregunta_frecuente(id_intencion, pregunta, respuesta, categoria)
SELECT i.id_intencion, v.p, v.r, v.c
FROM intencion i JOIN (VALUES
 ('buscar_libro','¿Cómo busco un libro?','Usa la opción Buscar: escribe título, autor o tema. La búsqueda no distingue mayúsculas ni acentos.','Catálogo'),
 ('prestamo','¿Cuántos libros puedo llevar en préstamo?','Alumnos hasta 2 libros por 5 días hábiles; docentes hasta 3 libros por 10 días hábiles. Los sábados y domingos no cuentan.','Préstamos'),
 ('reglas','¿Qué necesito para que me presten un libro?','No tener multas pendientes ni préstamos vencidos, no exceder tu límite de libros y que el libro esté disponible y sea de préstamo externo.','Préstamos'),
 ('renovacion','¿Puedo renovar un préstamo?','Sí, mientras no esté vencido, no tengas multas pendientes, nadie esté en lista de espera del libro y no superes tus renovaciones (alumnos 2, docentes 3). Cada renovación suma otro periodo completo.','Préstamos'),
 ('multas','¿Cuánto cuesta un retraso?','La multa es de $10.00 MXN por día hábil de retraso y por libro. Se paga en Tesorería y el bibliotecario registra el pago.','Multas'),
 ('multas','¿Qué pasa si pierdo un libro?','Se cobra el valor de reposición: el precio de la última compra en dólares por el tipo de cambio del día, más las multas por retraso acumuladas.','Multas'),
 ('horarios','¿Cuál es el horario de la biblioteca?','De lunes a viernes de 8:00 a 20:00 y sábados de 9:00 a 14:00.','Servicios'),
 ('ubicacion','¿Dónde encuentro un libro?','Busca el libro en Buscar y localizar: la ficha indica planta, pasillo, librero y nivel.','Catálogo'),
 ('recuperar_contrasena','Olvidé mi contraseña, ¿qué hago?','En la pantalla de inicio de sesión elige "Olvidé mi contraseña" e ingresa tu correo institucional.','Cuenta'),
 ('solicitar_compra','¿Cómo solicito que compren un libro?','El personal de compras registra una solicitud con título, cantidad y precio estimado desde el módulo Compras.','Compras'),
 ('buscar_libro','¿Qué significa consulta interna?','Los libros de consulta interna solo pueden leerse dentro de la biblioteca, no se prestan. Los reservados se consultan en mostrador.','Catálogo'),
 ('ayuda','¿Qué puedes hacer?','Puedo buscar libros, explicar las reglas de préstamo, renovación y multas, y (con sesión iniciada) consultar tus préstamos y adeudos.','Asistente'),
 ('pasar_a_bibliotecario','Quiero hablar con un bibliotecario','Registré tu solicitud; un bibliotecario revisará la conversación y te responderá.','Asistente'),
 ('no_entendido','No entendí tu pregunta','No logré entender tu pregunta. ¿Quieres reformularla o hablar con un bibliotecario?','Asistente')
) v(intencion,p,r,c) ON v.intencion = i.nombre;
