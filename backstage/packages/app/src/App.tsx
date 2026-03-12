import React from 'react';
import { createApp } from '@backstage/app-defaults';
import { AppRouter, FlatRoutes } from '@backstage/core-app-api';
import { CatalogIndexPage, CatalogEntityPage } from '@backstage/plugin-catalog';
import { ScaffolderPage } from '@backstage/plugin-scaffolder';
import { SearchPage } from '@backstage/plugin-search';
import { TechDocsIndexPage, TechDocsReaderPage } from '@backstage/plugin-techdocs';
import { UserSettingsPage } from '@backstage/plugin-user-settings';
import { ApiExplorerPage } from '@backstage/plugin-api-docs';
import { CatalogGraphPage } from '@backstage/plugin-catalog-graph';
import { CatalogImportPage } from '@backstage/plugin-catalog-import';
import { Route } from 'react-router-dom';
import { Root } from './components/Root';
import { entityPage } from './components/catalog/EntityPage';

const app = createApp({
  // Backstage plugins are configured via app-config.yaml
  // Additional plugin configurations can be added here
});

const routes = (
  <FlatRoutes>
    {/* Software Catalog */}
    <Route path="/" element={<CatalogIndexPage />} />
    <Route path="/catalog" element={<CatalogIndexPage />} />
    <Route path="/catalog/:namespace/:kind/:name" element={<CatalogEntityPage />}>
      {entityPage}
    </Route>

    {/* API Explorer */}
    <Route path="/api-docs" element={<ApiExplorerPage />} />

    {/* Software Templates (Golden Paths) */}
    <Route path="/create" element={<ScaffolderPage />} />

    {/* TechDocs */}
    <Route path="/docs" element={<TechDocsIndexPage />} />
    <Route path="/docs/:namespace/:kind/:name/*" element={<TechDocsReaderPage />} />

    {/* Search */}
    <Route path="/search" element={<SearchPage />} />

    {/* Catalog Import */}
    <Route path="/catalog-import" element={<CatalogImportPage />} />

    {/* Catalog Graph */}
    <Route path="/catalog-graph" element={<CatalogGraphPage />} />

    {/* User Settings */}
    <Route path="/settings" element={<UserSettingsPage />} />
  </FlatRoutes>
);

export default app.createRoot(
  <AppRouter>
    <Root>{routes}</Root>
  </AppRouter>,
);
