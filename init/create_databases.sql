
CREATE USER appuser WITH ENCRYPTED PASSWORD 'secret';

CREATE DATABASE orders
  WITH OWNER = appuser
       ENCODING = 'UTF8'
       LC_COLLATE = 'C'
       LC_CTYPE = 'C'
       TEMPLATE template0;

CREATE DATABASE payments
  WITH OWNER = appuser
       ENCODING = 'UTF8'
       LC_COLLATE = 'C'
       LC_CTYPE = 'C'
       TEMPLATE template0;
