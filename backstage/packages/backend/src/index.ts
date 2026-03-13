/*
 * Backstage Backend — new backend system
 * See: https://backstage.io/docs/backend-system/
 */
import { createBackend } from '@backstage/backend-defaults';

const backend = createBackend();

// Core plugins
backend.add(import('@backstage/plugin-app-backend'));
backend.add(import('@backstage/plugin-proxy-backend'));

// Auth
backend.add(import('@backstage/plugin-auth-backend'));

// Catalog
backend.add(import('@backstage/plugin-catalog-backend'));

// Scaffolder (Software Templates)
backend.add(import('@backstage/plugin-scaffolder-backend'));

// TechDocs
backend.add(import('@backstage/plugin-techdocs-backend'));

// Search
backend.add(import('@backstage/plugin-search-backend'));
backend.add(import('@backstage/plugin-search-backend-module-catalog'));
backend.add(import('@backstage/plugin-search-backend-module-techdocs'));

// Kubernetes
backend.add(import('@backstage/plugin-kubernetes-backend'));

backend.start();
