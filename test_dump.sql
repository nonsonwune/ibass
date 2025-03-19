--
-- PostgreSQL database dump
--

-- Dumped from database version 16.7 (Debian 16.7-1.pgdg120+1)
-- Dumped by pg_dump version 16.8 (Homebrew)

-- Started on 2025-03-19 11:00:47 WAT

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 221 (class 1259 OID 16998)
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: nuf_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO nuf_user;

--
-- TOC entry 3625 (class 0 OID 16998)
-- Dependencies: 221
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: nuf_user
--

COPY public.alembic_version (version_num) FROM stdin;
add_university_id_to_comment
\.


--
-- TOC entry 3481 (class 2606 OID 17026)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: nuf_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


-- Completed on 2025-03-19 11:01:09 WAT

--
-- PostgreSQL database dump complete
--

