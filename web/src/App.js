import React, { Component } from 'react';
import { Navbar, Nav, Form, Button } from 'react-bootstrap';
import { LinkContainer } from 'react-router-bootstrap';
import { Switch, Route, Link, withRouter } from 'react-router-dom';
import Section from './Section.js';
import Info from './Info.js';
import DriveInfo from './DriveInfo.js';
import Api from './Api.js';
import { POST_COUNT } from './config.js';
import './App.css';

class App extends Component {
  constructor(props) {
    super(props);

    this.state = {
      sections: null,
      defaultSection: null,
      prefixes: null,
      info: null,
    };
    this.isActive = this.isActive.bind(this);
    this.brandClicked = this.brandClicked.bind(this);
    this.getInfo = this.getInfo.bind(this);
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
  createSectionPath(path) {
    // Append the optional URL parameter `page` to a valid section path.
    return path + "/:page?";
  }
  getSections() {
    this.getCachedResource("sections", Api.getSections, (sections) => {
      let defaultSection;
      Object.entries(sections).forEach(([sectionName, section]) => {
        section.path_name = sectionName;
        section.path = "/" + sectionName;
        if (section.name === process.env.REACT_APP_DEFAULT_SECTION) defaultSection = section;
      });
      this.setState({ sections, defaultSection });
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

  componentDidMount() {
    this.getSections();
    this.getPrefixes();
    this.getInfo();
  }
  render() {
    return (
      <div className="App">
        <Navbar bg="light" expand="lg">
          <Nav.Link className="p-0" onClick={this.brandClicked}>
            <Navbar.Brand>{process.env.REACT_APP_WEBSITE_NAME}</Navbar.Brand>
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
            <Form inline>
              <Form.Control type="text" placeholder="Search" className="mr-sm-2"/>
              <Button variant="outline-primary">Search</Button>
            </Form>
          </Navbar.Collapse>
        </Navbar>
        <div className="main-content flex-grow-1">
          <Switch>
            {(this.state.sections === null || this.state.prefixes === null) && (
              <Route path="*">
                <Section section={null}/>
              </Route>
            )}
            <Route path="/info">
              <Info info={this.state.info} updateInfo={this.getInfo}/>
            </Route>
            <Route path="/drive-info">
              <DriveInfo info={this.state.info}/>
            </Route>
            {
              Object.entries(this.state.sections || {}).map(([sectionName, section]) => {
                return (
                  <Route path={this.createSectionPath(section.path)} key={section.path}>
                    <Section section={section} prefixes={this.state.prefixes}/>
                  </Route>
                );
              })
            }
            <Route path={this.createSectionPath("")}>
              <Section section={this.state.defaultSection} prefixes={this.state.prefixes}/>
            </Route>
          </Switch>
        </div>
      </div>
    );
  }
}

export default withRouter(App);
