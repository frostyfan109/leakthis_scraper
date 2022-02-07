import React, { Component } from 'react';
import { Navbar, Nav, Form, Button } from 'react-bootstrap';
import { LinkContainer } from 'react-router-bootstrap';
import { ToastContainer } from 'react-toastify';
import { Switch, Route, Link, Redirect, withRouter, generatePath, matchPath } from 'react-router-dom';
import Section from './Section.js';
import Info from './Info.js';
import DriveInfo from './DriveInfo.js';
import { QueryParamsPageComponent } from './QueryParams';
import Api from './Api.js';
import { socket } from './socket';
import { POST_COUNT, STATIC_URL } from './config.js';
import debounce from 'debounce-promise';
import qs from 'qs';
import './App.css';
import 'react-toastify/dist/ReactToastify.css';

class App extends QueryParamsPageComponent {
  constructor(props) {
    super(props);

    this.state = {
      sections: null,
      defaultSection: null,
      prefixes: null,
      info: null,
      searchQuery: undefined,
      realSearchQuery: undefined
    };
    this.isActive = this.isActive.bind(this);
    this.brandClicked = this.brandClicked.bind(this);
    this.getInfo = this.getInfo.bind(this);
    this._getUpdatePostsAborter = this._getUpdatePostsAborter.bind(this);
    
    this.updateSearchParam = debounce(this.updateSearchParam.bind(this), 250);
  }
  loading() {
    return (
      this.state.sections === null ||
      this.state.prefixes === null
    );
  }
  isActive(section, match, location) {
    if (match) return true;
    // Make sure that the index matches to the default section
    if (location.pathname === "/" && section == this.state.defaultSection) return true;
  }
  brandClicked(e) {
    this.props.history.push("/");
  }
  setSearchQuery(value) {
    // this.setState({ searchQuery : value });
    if (value === "") value = undefined;
    this.setState({ searchQuery : value });
    this.updateSearchParam(value);
  }
  updateSearchQuery() {
    const newQuery = this.getQuery();
    // const newValue = newQuery.query === undefined ? "" : newQuery.query;
    this.setState({ searchQuery : newQuery.query });
    this.setState({ realSearchQuery : newQuery.query });
  }
  updateSearchParam(value) {
    let activeSection = undefined;
    try {
      activeSection = this.getActiveSection();
    } catch {
      // skeleton state, sections undefined.
    }
    this.props.history.push({
      pathname: activeSection ? generatePath(this.createSectionPath(activeSection.path), {page: 1}) : this.props.location.pathname,
      search: super.setQueryParams(this.props.location, { "query" : value })
    });
    // this.setPage(1, super.setQueryParams(this.props.location, { "query" : value }));
    this.setState({ realSearchQuery : value });
  }
  createSectionPath(path) {
    // Append the optional URL parameter `page` to a valid section path.
    return path + "/:page?";
  }
  getActiveSection() {
    return Object.values(this.state.sections).find((section) => {
      const path = this.createSectionPath(section.path);
      if (matchPath(this.props.location.pathname, path)) return section;
    });
  }
  getSections() {
    this.getCachedResource("sections", Api.getSections, (sections) => {
      let defaultSection;
      Object.entries(sections).forEach(([sectionName, section]) => {
        section.path_name = sectionName;
        section.path = "/" + sectionName;
        if (section.name === process.env.REACT_APP_DEFAULT_SECTION) defaultSection = section;
      });
      if (JSON.stringify(sections) !== JSON.stringify(this.state.sections)) this.setState({ sections, defaultSection });
    });
  }
  getPrefixes() {
    this.getCachedResource("prefixes", Api.getPrefixes, (prefixes) => {
      this.setState({ prefixes });
    });
  }
  async getCachedResource(storageName, getter, setter) {
    let resources = localStorage.getItem(storageName);
    let wasCached = false;
    // If `sections` is cached, grab it until the request completes
    if (resources) {
      resources = JSON.parse(resources);
      wasCached = true;
    } else {
      resources = await getter();
    }
    setter(resources);

    // If the sections were cached, request the uncached version in case changes have been made.
    if (wasCached) {
      resources = await getter();
      setter(resources);
    }
    // Cache the newest version of the sections.
    localStorage.setItem(storageName, JSON.stringify(resources));
  }
  async getInfo(options) {
    const info = await Api.getInfo(options);
    this.setState({ info });
  }
  _getUpdatePostsAborter() {
    if (this._updatePostsController) this._updatePostsController.abort();
    this._updatePostsController = new AbortController();
    return this._updatePostsController;
  }
  getQuery() {
    return qs.parse(this.props.location.search, {ignoreQueryPrefix: true});
  }
  componentDidUpdate(prevProps) {
    if (this.props.location !== prevProps.location) {
      // Location changed; check if query string is the same
      const newQuery = this.getQuery();
      const oldQuery = qs.parse(prevProps.location.search, {ignoreQueryPrefix: true});
      if (newQuery.query !== oldQuery.query) {
        // Relevant query parameters have changed. Update posts.
        this.updateSearchQuery()
      }
    }
  }
  componentDidMount() {
    this.getSections();
    this.getPrefixes();
    this.getInfo();
    this.updateSearchQuery();
  }
  render() {
    if (this.props.location.pathname === "/" && this.state.defaultSection) return <Redirect to={this.state.defaultSection.path}/>;
    return (
      <div className="App h-auto" style={{minHeight: "100%"}}>
        <Navbar bg="light" expand="lg" sticky="top">
          <Nav.Link className="p-0" onClick={this.brandClicked}>
            <Navbar.Brand>
              <img
                src={STATIC_URL + "/logo.png"}
                className="d-inline h-auto"
                width="100px"
              />
              {/* {process.env.REACT_APP_WEBSITE_NAME} */}
              </Navbar.Brand>
          </Nav.Link>
          <Navbar.Toggle aria-controls="basic-navbar-nav"/>
          <Navbar.Collapse>
            <Nav className="mr-auto">
              {
                Object.entries(this.state.sections || {}).map(([sectionName, section]) => (
                    /* Although it looks strange to have active as always false and then use isActive, it circumvents
                     * a bug which causes two LinkContainers to be active at once when clicking on the Navbar.Brand
                     */
                    <LinkContainer to={section.path} active={false} isActive={(match, location) => this.isActive(section, match, location)} key={section.path}>
                      <Nav.Link>{section.name}</Nav.Link>
                    </LinkContainer>
                ))
              }
              <div className="border-left m-2 d-none d-lg-block">{/* separator */}</div>
              <LinkContainer to="/info" active={false} isActive={(match, location) => this.isActive(null, match, location)}>
                <Nav.Link>Info</Nav.Link>
              </LinkContainer>
              <div className="border-left m-2 d-none d-lg-block">{/* separator */}</div>
              <LinkContainer to="/drive-info" active={false} isActive={(match, location) => this.isActive(null, match, location)}>
                <Nav.Link>Drive</Nav.Link>
              </LinkContainer>
            </Nav>
            <div className="m-2 m-lg-0"/>
            <Form inline onSubmit={(e) => e.preventDefault()}>
              <Form.Control type="text"
                            placeholder="Search"
                            className="mr-sm-2"
                            value={this.state.searchQuery || ""}
                            onChange={(e) => this.setSearchQuery(e.target.value)}/>
            </Form>
          </Navbar.Collapse>
        </Navbar>
        <div className="main-content flex-grow-1">
          <ToastContainer
            position="top-right"
            autoclose={2500}
            hideProgressBar={false}
            newestOnTop={false}
            draggable={false}
            closeOnClick
            pauseOnFocusLoss
            pauseOnHover/>
          <Switch ref={(el) => {window.el = el;}}>
            {(this.state.sections === null || this.state.prefixes === null) && (
              <Route path="*">
                <Section section={null} searchQuery={this.state.realSearchQuery}/>
              </Route>
            )}
            <Route path="/info">
              <Info info={this.state.info} updateInfo={this.getInfo}/>
            </Route>
            <Route path="/drive-info">
              <DriveInfo info={this.state.info} searchQuery={this.state.realSearchQuery}/>
            </Route>
            {
              Object.entries(this.state.sections || {}).map(([sectionName, section]) => {
                return (
                  <Route path={this.createSectionPath(section.path)} key={section.path}>
                    <Section section={section} prefixes={this.state.prefixes} searchQuery={this.state.realSearchQuery} getUpdatePostsAborter={this._getUpdatePostsAborter}/>
                  </Route>
                );
              })
            }
            {/* <Route path={this.createSectionPath("")}>
              <Section section={this.state.defaultSection} prefixes={this.state.prefixes} searchQuery={this.state.realSearchQuery}/>
            </Route> */}
          </Switch>
        </div>
      </div>
    );
  }
}

export default withRouter(App);