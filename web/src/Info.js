import React, { Component } from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import { Line } from 'react-chartjs-2';
import { Table, Modal, Form, Card, ListGroup, Tabs, Tab } from 'react-bootstrap';
import { FaChartBar } from 'react-icons/fa';
import { linkToPost } from './common.js';
import Api from './Api.js';
import prettyBytes from 'pretty-bytes';
import debounce from 'debounce-promise';
import moment from 'moment';

export default class Info extends Component {
  constructor(props) {
    super(props);

    this.state = {
      errorModal: false,
      dependencyModal: false,
      configLoading: {},
      configTemp: null,
      scrapeGraphSort: "days",
      range: null,
      loadingGraph: false
    };
    // this.rangeChanged = debounce(this.rangeChanged.bind(this), 300);
    this.rangeChanged = this.rangeChanged.bind(this);
    // this.setRange = this.setRange.bind(this);
    this.updateSort = this.updateSort.bind(this);
    this.updateConfig = this.updateConfig.bind(this);
    this.canvasMounted = this.canvasMounted.bind(this);
    this.updateTimeoutInterval = this.updateTimeoutInterval.bind(this);

    this.debounceUpdateInfo = debounce(this.updateInfo, 300);
    this.debounceUpdateTimeoutInterval = debounce((value) => this.updateConfig({timeout_interval: value}), 500);
  }
  async rangeChanged(e) {
    this.setState({ range: e.target.value, loadingGraph: true });
    await this.debounceUpdateInfo();
    this.setState({ loadingGraph: false });
    // this.props.updateInfo();
  }
  updateTimeoutInterval(e) {
    const { value } = e.target;
    const { configTemp } = this.state;
    configTemp.scraper_config.timeout_interval = value;
    this.setState({ configTemp });
    this.debounceUpdateTimeoutInterval(value);
  }
  updateInfo() {
    return this.props.updateInfo({ sort: this.state.scrapeGraphSort, range: this.state.range });
  }
  // setRange(e) {
    // this.setState({ range: e.target.value }, () => {
    //   this.props.updateInfo();
    // }
    // });
  updateSort(e) {
    const scrapeGraphSort = e.target.value;
    this.setState({
      scrapeGraphSort,
      range: this.props.info.data.scrape_data.data[scrapeGraphSort].range || this.props.info.data.scrape_data.data[scrapeGraphSort].default
    });
  }
  async updateConfig(options) {
    let configLoading = this.state.configLoading;
    Object.keys(options).forEach((option) => {
      configLoading[option] = true;
    });
    this.setState({ configLoading });
    await Api.updateConfig(options);
    await this.updateInfo();
    configLoading = this.state.configLoading;
    Object.keys(options).forEach((option) => {
      configLoading[option] = false;
    });
    this.setState({ configLoading });
  }
  updateDefaultRange() {
    if (this.state.range === null && this.props.info !== null) {
      const scrapeGraphSort = this.state.scrapeGraphSort;
      this.setState({ range: this.props.info.data.scrape_data.data[scrapeGraphSort].range || this.props.info.data.scrape_data.data[scrapeGraphSort].default });
    }
  }
  canvasMounted(canvasRef) {
    if (canvasRef) {
      const canvas = canvasRef.chartInstance.canvas;
      canvas.classList.add("chartjs-canvas");
    }
  }
  componentDidUpdate() {
    this.updateDefaultRange();
    if (this.state.configTemp === null && this.props.info !== null) this.setState({ configTemp : this.props.info.config });
  }
  componentDidMount() {
    this.updateDefaultRange();
  }
  render() {
    if (this.props.info === null || this.state.configTemp === null) return null;
    const { info: { data, status: {account_info, ...status}, config, environment, meta } } = this.props;
    // console.log(this.props);
    return (
      <div className="py-4 px-4 w-100 h-100 d-flex flex-column">
        <Helmet>
          <title>Scraper Info</title>
        </Helmet>
        <div className="mb-4 d-none">
          <h4 className="mb-0">Scraper Info</h4>
          {/*<small></small>*/}
        </div>
        <div className="d-flex flex-column flex-md-row align-items-md-start">
          <div style={{flex: 0, flexGrow: 2, height: "100%"}} className="d-flex flex-column">
            <div className="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center mb-2">
              <h5 className="h6">Scraping Data</h5>

              <div className="graph-controls d-flex float-right align-items-center">
                {
                  this.state.range !== null && (
                    <div className="d-flex mr-2 flex-grow-1">
                    <Form.Control type="range"
                                  custom
                                  ref={(ref) => this._range = ref}
                                  onChange={this.rangeChanged}
                                  value={this.state.range}
                                  min={data.scrape_data.data[this.state.scrapeGraphSort].min}
                                  max={data.scrape_data.data[this.state.scrapeGraphSort].max}/>
                    <span className="ml-2">{this.state.range}</span>
                    </div>
                  )
                }
                {/*<Form.Control className="w-auto" type="number" size="sm"/>*/}
                <Form.Control className="custom-select custom-select-sm w-auto ml-2"
                              as="select"
                              size="sm"
                              value={this.state.scrapeGraphSort}
                              onChange={this.updateSort}>
                  <option value="days">Days</option>
                  <option value="weeks">Weeks</option>
                  <option value="months">Months</option>
                </Form.Control>
              </div>
            </div>
            {
              this.state.loadingGraph ? (
                <div className="d-flex justify-content-center align-items-center flex-column flex-grow-1">
                  <svg xmlns="http://www.w3.org/2000/svg" xmlnsXlink="http://www.w3.org/1999/xlink" style={{background: "rgb(255, 255, 255)", display: "block", shapeRendering: "auto"}} width="100px" height="100px" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid">
                  <g transform="rotate(180 50 50)"><rect x="15" y="15" width="10" height="40" fill="#abbd81">
                  <animate attributeName="height" values="50;70;30;50" keyTimes="0;0.33;0.66;1" dur="1s" repeatCount="indefinite" calcMode="spline" keySplines="0.5 0 0.5 1;0.5 0 0.5 1;0.5 0 0.5 1" begin="-0.4s"></animate>
                  </rect><rect x="35" y="15" width="10" height="40" fill="#f8b26a">
                  <animate attributeName="height" values="50;70;30;50" keyTimes="0;0.33;0.66;1" dur="1s" repeatCount="indefinite" calcMode="spline" keySplines="0.5 0 0.5 1;0.5 0 0.5 1;0.5 0 0.5 1" begin="-0.2s"></animate>
                  </rect><rect x="55" y="15" width="10" height="40" fill="#f47e60">
                  <animate attributeName="height" values="50;70;30;50" keyTimes="0;0.33;0.66;1" dur="1s" repeatCount="indefinite" calcMode="spline" keySplines="0.5 0 0.5 1;0.5 0 0.5 1;0.5 0 0.5 1" begin="-0.6s"></animate>
                  </rect><rect x="75" y="15" width="10" height="40" fill="#e15b64">
                  <animate attributeName="height" values="50;70;30;50" keyTimes="0;0.33;0.66;1" dur="1s" repeatCount="indefinite" calcMode="spline" keySplines="0.5 0 0.5 1;0.5 0 0.5 1;0.5 0 0.5 1" begin="-1s"></animate>
                  </rect></g></svg>
                  Loading
                </div>
              ) : (
                <Line redraw data={{
                  labels: data.scrape_data.data[this.state.scrapeGraphSort].labels,
                  datasets: [{
                    data: data.scrape_data.data[this.state.scrapeGraphSort].data,
                    lineTension: 0,
                    backgroundColor: "transparent",
                    borderColor: "#007bff",
                    borderWidth: 4,
                    pointBackgroundColor: "#007bff"
                  }]
                }} options={{
                  scales: {
                    yAxes: [{
                      scaleLabel: {
                        display: true,
                        labelString: "Posts"
                      },
                      ticks: {
                        beginAtZero: false
                      }
                    }]
                  },
                  legend: {
                    display: false
                  },
                  maintainAspectRatio: true
                }} ref={this.canvasMounted}/>
              )
            }
          </div>
          <div className="d-flex flex-column">
            <Card className="info environment-table ml-md-3 mt-0 mt-3 mt-md-0" style={{flexGrow: 1, flexBasis: 0}}>
              <h6><Card.Header>System Environment</Card.Header></h6>
              <Card.Body>
                <Table>
                  <tbody>
                    <tr>
                      <td>OS Platform</td>
                      <td>{environment.platform}</td>
                    </tr>
                    <tr>
                      <td>OS Arch</td>
                      <td>{environment.arch}</td>
                    </tr>
                    <tr>
                      <td>OS Release</td>
                      <td>{environment.release}</td>
                    </tr>
                    <tr>
                      <td>Python Version</td>
                      <td>Python {environment.version.join(".")}</td>
                    </tr>
                    <tr>
                      <td>Virtual Environment</td>
                      <td>{JSON.stringify(environment.virtualenv)}</td>
                    </tr>
                    <tr>
                      <td>Installed Dependencies</td>
                      <td style={{overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis", maxWidth: "0"}}>
                        <a href="javascript:void(0);"
                          className="text-reset"
                          onClick={(e) => this.setState({dependencyModal: true})}>
                          {environment.dependencies.find((d) => d.name === "Installed").dependencies.map((d) => d.name).join(", ")}
                        </a>
                      </td>
                    </tr>
                    <tr>
                      <td>Timezone</td>
                      <td>{environment.timezone}</td>
                    </tr>
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
            <Card className="info environment-var-table ml-md-3 mt-3" style={{flexGrow: 1, flexBasis: 0}}>
              <h6><Card.Header>Environment Variables</Card.Header></h6>
              <Card.Body>
                <Table>
                  <tbody>
                    {
                      Object.entries(environment.environment_vars).map(([envVar, value]) => (
                        <tr key={envVar}>
                          <td style={{width: "50%"}}>{envVar}</td>
                          <td style={{width: "50%", maxWidth: "0"}}><span>{value}</span></td>
                        </tr>
                      ))
                    }
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </div>
        </div>
        <div className="flex-grow-1 d-flex flex-column flex-md-row align-items-md-start mt-3">
          <Card className="info status-table">
            <h6><Card.Header>Status</Card.Header></h6>
            <Card.Body>
              <Table>
                <tbody>
                  <tr>
                    <td>Running</td>
                    <td>{JSON.stringify(status.running)}</td>
                  </tr>
                  <tr>
                    <td>PID</td>
                    <td>{status.pid}</td>
                  </tr>
                  <tr>
                    <td>Last scraped</td>
                    <td>{moment(status.last_scraped * 1000).fromNow()}</td>
                  </tr>
                  <tr>
                    <td>Last error</td>
                    <td style={{overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis", maxWidth: "0"}}>{status.last_error === null ? "None" : (
                      <a href="javascript:void(0);"
                         className="text-reset"
                         onClick={(e) => this.setState({errorModal: true})}>
                        {status.last_error.error} ({moment(status.last_error.time * 1000).fromNow()})
                      </a>
                    )}</td>
                  </tr>
                  <tr>
                    <td>Most recent post</td>
                    <td>
                      {
                        status.most_recent_post === null ? "None" : (
                          <Link to={linkToPost(status.most_recent_post)} className="text-reset">
                            {status.most_recent_post.title} ({moment(status.most_recent_post.first_scraped * 1000).fromNow()})
                          </Link>
                        )
                      }
                    </td>
                  </tr>
                </tbody>
              </Table>
            </Card.Body>
          </Card>
          <Card className="info config-table ml-md-3 mt-0 mt-3 mt-md-0">
            <h6><Card.Header>Config</Card.Header></h6>
            <Card.Body>
              <Table>
                <tbody>
                  <tr>
                    <td>Log scraped posts</td>
                    {/*<td>{JSON.stringify(config.debug_config.print_posts_scraped)}</td>*/}
                    <td>
                      <BoolSelect value={config.scraper_config.print_posts_scraped}
                                  selectProps={{disabled: this.state.configLoading.print_posts_scraped}}
                                  onChange={(e) => this.updateConfig({print_posts_scraped: JSON.parse(e.target.value)})}/>
                    </td>
                  </tr>
                  <tr>
                    <td>Log level</td>
                    <td>
                      <Form.Control className="custom-select custom-select-sm w-auto"
                                    as="select"
                                    size="sm"
                                    value={config.scraper_config.log_level}
                                    onChange={(e) => this.updateConfig({log_level: e.target.value})}
                                    disabled={this.state.configLoading.log_level}>
                        {
                          meta.log_levels.map((level) => <option key={level} value={level}>{level}</option>)
                        }
                      </Form.Control>
                    </td>
                  </tr>
                  <tr>
                    <td>Timeout interval</td>
                    <td>
                      <Form.Control className="w-auto"
                                    size="sm"
                                    type="number"
                                    value={this.state.configTemp.scraper_config.timeout_interval}
                                    onChange={this.updateTimeoutInterval}
                                    disabled={this.state.configLoading.timeout_interval}>
                      </Form.Control>
                    </td>
                  </tr>
                  <tr>
                    <td>Update posts</td>
                    <td>
                      <BoolSelect value={config.scraper_config.update_posts}
                                  selectProps={{disabled: this.state.configLoading.update_posts}}
                                  onChange={(e) => this.updateConfig({update_posts: JSON.parse(e.target.value)})}/>
                    </td>
                  </tr>
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </div>
        <div className="flex-grow-1 d-flex flex-column flex-md-row align-items-md-start mt-3">
          <Card className="info data-table flex-grow-1">
            <h6><Card.Header>Data</Card.Header></h6>
            <Card.Body>
              <Table>
                <tbody>
                  <tr>
                    <td>Post count</td>
                    <td>{data.scrape_data.post_count}</td>
                  </tr>
                  <tr>
                    <td>File count</td>
                    <td>{data.scrape_data.known_file_count} ({data.scrape_data.total_file_count})</td>
                  </tr>
                </tbody>
              </Table>
            </Card.Body>
          </Card>
          <Card className="info credentials-table ml-md-3 mt-0 mt-3 mt-md-0">
            <h6><Card.Header>Account Credentials</Card.Header></h6>
            <Card.Body>
              <Table>
                <tbody>
                  <tr>
                    <td>LT username</td>
                    <td>{account_info.leakthis_username}</td>
                  </tr>
                  <tr>
                    <td>LT password</td>
                    <td>{account_info.leakthis_password}</td>
                  </tr>
                  <tr style={{display: "none"}}>
                    <td>Drive account</td>
                    <td>{account_info.drive_user}</td>
                  </tr>
                  {/* <tr>
                    <td>LT user-agent</td>
                    <td style={{overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis", maxWidth: "0"}}>{account_info.leakthis_user_agent}</td>
                  </tr> */}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </div>
        <div className="flex-grow-1 d-flex flex-column flex-md-row align-items-md-start mt-3">
          <Card className="info drive-table flex-grow-1">
            <h6><Card.Header>Drive info</Card.Header></h6>
            <Card.Body>
              <Table>
                <tbody>
                  {
                    Object.entries(account_info.drive).map(([project_id, project_data]) => (
                      <tr>
                        <td>{project_id}</td>
                        <td>
                          {prettyBytes(project_data.quota_used).replace(" ", "")} of {prettyBytes(Math.round(project_data.quota_total / 1E9) * 1E9).replace(" ", "")}
                        </td>
                        <td>{project_data.in_use ? "Active" : (project_data.available ? "Available" : "Full")}</td>
                      </tr>
                    ))
                  }
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </div>

        <Modal centered size="lg" scrollable show={this.state.errorModal} onHide={() => this.setState({errorModal: false})} aria-labelledby="errorModalTitle">
          <Modal.Header closeButton>
            <Modal.Title id="errorModalTitle">Traceback</Modal.Title>
          </Modal.Header>
          <Modal.Body className="">
            <pre>{status.last_error.traceback}</pre>
          </Modal.Body>
        </Modal>
        <Modal centered scrollable show={this.state.dependencyModal} onHide={() => this.setState({dependencyModal: false})} aria-labelledby="dependencyModalTitle">
          <Modal.Header closeButton>
            <Modal.Title id="dependencyModalTitle">Dependencies</Modal.Title>
          </Modal.Header>
          <Modal.Body className="p-3">
            {/*<ListGroup>
              {environment.dependencies.map((dependency) => <ListGroup.Item className="p-1" key={dependency}>{dependency}</ListGroup.Item>)}
            </ListGroup>*/}
            <Tabs defaultActiveKey={environment.dependencies[0].name} id="dependencyTabs">
              {
                environment.dependencies.map((dependencyData) => (
                  <Tab eventKey={dependencyData.name} key={dependencyData.name} title={dependencyData.name}>
                    <Table striped>
                      <tbody>
                        {dependencyData.dependencies.map((dependency) => (
                            <tr key={dependency.name}>
                              <td>{dependency.name}</td>
                              <td>{dependency.version}</td>
                            </tr>
                        ))}
                      </tbody>
                    </Table>
                  </Tab>
                ))
              }
            </Tabs>
          </Modal.Body>
        </Modal>
      </div>
    );
  }
}

function BoolSelect({value, onChange, selectProps}) {
  return (
    <Form.Control className="custom-select custom-select-sm w-auto"
                  as="select"
                  size="sm"
                  value={value}
                  onChange={onChange}
                  {...selectProps}>
      <option value={true}>true</option>
      <option value={false}>false</option>
    </Form.Control>
  );
}