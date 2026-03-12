import React, { PropsWithChildren } from 'react';
import { makeStyles } from '@material-ui/core';
import HomeIcon from '@material-ui/icons/Home';
import ExtensionIcon from '@material-ui/icons/Extension';
import LibraryBooksIcon from '@material-ui/icons/LibraryBooks';
import CreateComponentIcon from '@material-ui/icons/AddCircleOutline';
import SearchIcon from '@material-ui/icons/Search';
import CategoryIcon from '@material-ui/icons/Category';
import BuildIcon from '@material-ui/icons/Build';
import {
  Sidebar,
  SidebarDivider,
  SidebarGroup,
  SidebarItem,
  SidebarPage,
  SidebarSpace,
  useSidebarOpenState,
} from '@backstage/core-components';
import { SidebarSearchModal } from '@backstage/plugin-search';
import { Settings as SidebarSettings } from '@backstage/plugin-user-settings';

const useSidebarLogoStyles = makeStyles({
  root: {
    width: '100%',
    height: '3rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '1.5rem',
    fontWeight: 'bold',
  },
});

const SidebarLogo = () => {
  const classes = useSidebarLogoStyles();
  const { isOpen } = useSidebarOpenState();
  return (
    <div className={classes.root}>
      {isOpen ? 'Platform Portal' : 'PP'}
    </div>
  );
};

export const Root = ({ children }: PropsWithChildren<{}>) => (
  <SidebarPage>
    <Sidebar>
      <SidebarLogo />
      <SidebarGroup label="Search" icon={<SearchIcon />} to="/search">
        <SidebarSearchModal />
      </SidebarGroup>
      <SidebarDivider />
      <SidebarGroup label="Menu" icon={<HomeIcon />}>
        {/* Global nav */}
        <SidebarItem icon={HomeIcon} to="/" text="Catalog" />
        <SidebarItem icon={ExtensionIcon} to="/api-docs" text="APIs" />
        <SidebarItem icon={LibraryBooksIcon} to="/docs" text="TechDocs" />
        <SidebarItem icon={CreateComponentIcon} to="/create" text="Templates" />
        <SidebarDivider />
        {/* Platform Tools */}
        <SidebarItem icon={CategoryIcon} to="/catalog-graph" text="Graph" />
        <SidebarItem icon={BuildIcon} to="/catalog-import" text="Import" />
      </SidebarGroup>
      <SidebarSpace />
      <SidebarDivider />
      <SidebarGroup label="Settings" to="/settings">
        <SidebarSettings />
      </SidebarGroup>
    </Sidebar>
    {children}
  </SidebarPage>
);
