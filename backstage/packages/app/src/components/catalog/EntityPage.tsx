import React from 'react';
import { EntityLayout, EntitySwitch } from '@backstage/plugin-catalog';
import {
  EntityAboutCard,
  EntityHasApisCard,
  EntityHasComponentsCard,
  EntityHasSystemsCard,
  EntityLinksCard,
} from '@backstage/plugin-catalog';
import { EntityApiDefinitionCard } from '@backstage/plugin-api-docs';
import { EntityTechdocsContent } from '@backstage/plugin-techdocs';
import { EntityKubernetesContent } from '@backstage/plugin-kubernetes';
import { EntityArgoCDOverviewCard } from '@roadiehq/backstage-plugin-argo-cd';
import { Grid } from '@material-ui/core';

/**
 * Entity Page — shows per-service details in the catalog
 * Includes: Overview, CI/CD (Argo CD health), Kubernetes resources,
 * API definition, TechDocs
 */

const serviceEntityPage = (
  <EntityLayout>
    <EntityLayout.Route path="/" title="Overview">
      <Grid container spacing={3}>
        <Grid item md={6}>
          <EntityAboutCard variant="gridItem" />
        </Grid>
        <Grid item md={6}>
          <EntityLinksCard />
        </Grid>
        <Grid item md={6}>
          <EntityHasApisCard />
        </Grid>
        {/* Argo CD sync status per service */}
        <Grid item md={6}>
          <EntityArgoCDOverviewCard />
        </Grid>
      </Grid>
    </EntityLayout.Route>

    <EntityLayout.Route path="/kubernetes" title="Kubernetes">
      <EntityKubernetesContent refreshIntervalMs={30000} />
    </EntityLayout.Route>

    <EntityLayout.Route path="/api" title="API">
      <Grid container spacing={3}>
        <Grid item md={12}>
          <EntityApiDefinitionCard />
        </Grid>
      </Grid>
    </EntityLayout.Route>

    <EntityLayout.Route path="/docs" title="Docs">
      <EntityTechdocsContent />
    </EntityLayout.Route>
  </EntityLayout>
);

const systemEntityPage = (
  <EntityLayout>
    <EntityLayout.Route path="/" title="Overview">
      <Grid container spacing={3}>
        <Grid item md={6}>
          <EntityAboutCard variant="gridItem" />
        </Grid>
        <Grid item md={6}>
          <EntityHasComponentsCard variant="gridItem" />
        </Grid>
        <Grid item md={6}>
          <EntityHasApisCard variant="gridItem" />
        </Grid>
        <Grid item md={6}>
          <EntityHasSystemsCard variant="gridItem" />
        </Grid>
      </Grid>
    </EntityLayout.Route>
  </EntityLayout>
);

const defaultEntityPage = (
  <EntityLayout>
    <EntityLayout.Route path="/" title="Overview">
      <Grid container spacing={3}>
        <Grid item md={12}>
          <EntityAboutCard />
        </Grid>
      </Grid>
    </EntityLayout.Route>
  </EntityLayout>
);

export const entityPage = (
  <EntitySwitch>
    <EntitySwitch.Case if={e => e?.spec?.type === 'service'}>
      {serviceEntityPage}
    </EntitySwitch.Case>
    <EntitySwitch.Case if={e => e?.kind === 'System'}>
      {systemEntityPage}
    </EntitySwitch.Case>
    <EntitySwitch.Case>{defaultEntityPage}</EntitySwitch.Case>
  </EntitySwitch>
);
