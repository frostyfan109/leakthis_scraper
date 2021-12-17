import React, { Component } from 'react';
import { Helmet } from 'react-helmet';
import { FaEye, FaComment, FaTimes, FaThumbtack } from 'react-icons/fa';
import { IoIosPlay as FaPlay, IoIosPause as FaPause } from 'react-icons/io';
import { Link, withRouter, generatePath } from 'react-router-dom';
import { Card, Badge, Form, Button } from 'react-bootstrap';
import Pagination from 'react-js-pagination';
import { POST_COUNT } from './config.js';
import { abbrNum } from './common.js';
import Api from './Api.js';
import qs from 'qs';
import * as mm from 'music-metadata-browser';
import Skeleton from 'react-loading-skeleton';
import moment from 'moment';
import pluralize from 'pluralize';
import classNames from 'classnames';

class QueryParamsComponent extends Component {
  setQueryParams(location, params) {
    const search = new URLSearchParams(location.search);
    Object.keys(params).forEach((key) => {
      if (params[key] === undefined) {
        search.delete(key);
      } else {
        search.set(key, params[key]);
      }
    });
    return "?" + search.toString();
  }
};

class Post extends QueryParamsComponent {
  constructor(props) {
    super(props);
  }
  render() {
    let { post, skeleton, setPlaying, setPaused, playing: playingObj } = this.props;
    if (skeleton) {
      post = {
        prefixes: [],
        files: []
      };
      //
      setPlaying = () => {};
      setPaused = () => {}
    }
    let playing = false;
    let paused = false;
    let file = null;
    if (playingObj) {
      playing = post.id === playingObj.id;
      paused = playing && playingObj.paused;
      file = playingObj.file;
    }
    return (
      <Card className={classNames("Post mb-0 mb-md-2", skeleton && "skeleton")}>
        <Card.Body className="p-2 p-sm-3">
          <div className="media align-items-center">
            {/*<img className="mr-3 rounded-circle post-avatar"
                 src={!skeleton ? `${process.env.PUBLIC_URL}/default3.jpg` : undefined}
                 alt={!skeleton ? "User" : undefined}
                 width="50"
                 height="50"/>
            */}
            <div className={
                   classNames(
                     "d-flex justify-content-center align-items-center rounded-circle outer-player-container",
                     playing && "play",
                     paused && "paused",
                     playing ? "mr-3" : "mr-2"
                   )
                 }
                 style={{width: "50px", height: "50px"}}
                 onClick={() => !playing || paused ? setPlaying(post) : setPaused()}>
              <div className="rounded-circle inner-player-container">
                {
                  playing && !paused ? (
                    <>{/* Currently playing and not paused */}
                    <FaPause className="audio-player"/></>
                  ) : (
                    <>{/* Currently paused or not playing */}
                    <FaPlay className="audio-player"/></>
                  )
                }
              </div>
            </div>
            <div className="media-body mr-3 mr-md-0">
              <h6 className="post-header d-inline d-md-flex align-items-center">
                {
                  post.prefixes.map((prefix) => (
                    <>
                    <a href="javascript:void(0);" className="d-inline-block" onClick={() => !skeleton && this.props.setPrefix(prefix.prefix_id)}>
                      <span className="d-flex justify-content-center align-items-center">
                        {/* Badge has 3px margin-y on default. Add 2px to margin-top so adjust for text alignment. */}
                        <Badge style={{color: prefix.text_color, backgroundColor: prefix.bg_color, fontSize: ".75rem", paddingTop: "5px"}}>{prefix.name}</Badge>
                      </span>
                    </a>
                    &nbsp;
                    </>
                  ))
                }
                <a href="javascript:void(0);" className="text-body d-inline">{post.title}</a>
              </h6>
              {/*<p className="text-secondary">
                {post.body}
              </p>*/}
              <p className="text-muted mb-0 post-footer">
                <a href="javascript:void(0);" className="text-muted" onClick={() => this.props.updateAuthor(post.created_by)}>{post.created_by}</a>
                <span className="text-secondary">
                  &nbsp;&bull;&nbsp;{moment(post.created*1000).fromNow()}
                  &nbsp;&bull;&nbsp;{pluralize("file", post.files.length, true)}
                </span>
              </p>
            </div>
            <div className={classNames("text-muted small text-center align-self-center d-flex flex-column flex-md-row align-items-end", skeleton && "hidden")}>
              <span className=""><FaEye/> {abbrNum(post.view_count)}</span>
              <span className="ml-2"><FaComment/> {abbrNum(post.reply_count)}</span>
              {post.pinned && (
                <span className="ml-2"><FaThumbtack/></span>
              )}
            </div>
          </div>
        </Card.Body>
        {
          playing && (
            <div className="audio-player-controls p-2 d-flex flex-column align-items-center border-top bg-light">
              <div className="audio-player-info d-flex align-items-center">
                {}
              </div>
              <div className="bottom-controls d-flex align-items-center">
                {
                  playing && !paused ? (
                    <FaPause className="audio-player"/>
                  ) : (
                    <FaPlay className="audio-player"/>
                  )
                }
                <span className="progress-time progress-time-elapsed small">0:35</span>
                <div className="audio-progress rounded flex-grow-1">
                  <div className="audio-progress-bar rounded bg-primary">
                  </div>
                </div>
                <span className="progress-time progress-time-left small">3:23</span>
              </div>
            </div>
          )
        }
      </Card>
    );
  }
}

class Section extends QueryParamsComponent {
  constructor(props) {
    super(props);

    this.state = {
      posts: null,
      pages: null,
      hidePinned: false,
      playing: null
    };

    this.setPlaying = this.setPlaying.bind(this);
    this.setPaused = this.setPaused.bind(this);
    this.updateAuthor = this.updateAuthor.bind(this);
    this.clearAuthor = this.clearAuthor.bind(this);
    this.updateHidePinned = this.updateHidePinned.bind(this);
    this.updateSort = this.updateSort.bind(this);
    this.clearPrefix = this.clearPrefix.bind(this);
    this.setPage = this.setPage.bind(this);
    this.setPrefix = this.setPrefix.bind(this);

    this.SORT_BY = [
      "latest",
      "popular",
      "active"
    ];
  }
  setPlaying(post) {
    // if (this.state.paused && post.id === this.state.playing) {
    if (this.paused() && post.id === this.state.playing.id) {
      const { playing } = this.state;
      playing.paused = false;
      this.setState({ playing });
    }
    else this.setState({ playing: {
      id: post.id,
      file: post.files[0],
      paused: false
    }});
  }
  paused() {
    return this.state.playing && this.state.playing.paused;
  }
  setPaused() {
    const { playing } = this.state;
    playing.paused = true;
    this.setState({ playing });
  }
  setQueryParams(params) {
    // Set page back to 0.
    // this.setPage(1, super.setQueryParams(...args));
    // this.setPage(1);
    // return super.setQueryParams(...args);
    this.setPage(1, super.setQueryParams(this.props.location, params));
  }
  updateHidePinned(e) {
    e.preventDefault();
    // Switch the value
    const value = e.target.checked;
    localStorage.setItem("hidePinned", JSON.stringify(value));
    this.setState({ hidePinned: value }, () => {
      this.updatePosts();
    });
  }
  updateAuthor(author) {
    this.setQueryParams({"author": author})
  }
  clearAuthor() {
    this.setQueryParams({"author": undefined})
  }
  updateSort(e) {
    this.setQueryParams({"sort": e.target.value})
  }
  setPrefix(prefix) {
    this.setQueryParams({prefix})
  }
  clearPrefix(e) {
    this.setQueryParams({"prefix": undefined})
  }
  parsePrefix() {
    return this.getPrefix({prefix_id: parseInt(this.getQuery().prefix)});
  }
  getPrefix(props) {
    return this.props.prefixes.filter((prefix) => {
      return Object.keys(props).every((prop) => {
        const value = props[prop];
        // Weak check.
        return prefix[prop] === value;
      });
    })[0];
  }
  setPage(page, search) {
    console.log(this.props.match.path);
    console.log(generatePath(this.props.match.path, {page}), search)
    this.props.history.push({
      pathname: generatePath(this.props.match.path, {page}),
      search: search || this.props.location.search
    });
  }
  getPage() {
    return this.props.match.params.page ? parseInt(this.props.match.params.page) : 1;
  }
  getQuery() {
    return qs.parse(this.props.location.search, {ignoreQueryPrefix: true});
  }
  getTotalPages() {
    return this.state.posts === null ? null : this.state.posts.pages
  }
  pagination(upper, args) {
    return (
      this.state.posts !== null && (
        <Pagination innerClass="pagination"
                    itemClass="page-item"
                    linkClass="page-link"
                    itemClassPrev="page-item-prev"
                    itemClassNext="page-item-next"
                    itemClassFirst="page-item-first"
                    itemClassLast="page-item-last"
                    prevPageText="«"
                    nextPageText="»"
                    firstPageText="First"
                    lastPageText="Last"
                    hideFirstLastPages={upper}
                    activePage={this.getPage()}
                    itemsCountPerPage={this.state.posts.per_page}
                    totalItemsCount={this.state.posts.total}
                    pageRangeDisplayed={5}
                    onChange={this.setPage}
                    {...args}/>
      )
    );
  }
  async updatePosts() {
    console.log("Updating posts");
    const queryParams = qs.parse(this.props.location.search, {ignoreQueryPrefix: true});
    const sort = queryParams.sort;
    const prefix = queryParams.prefix;
    const author = queryParams.author;
    // Page parameter is optional. If it is omitted, it is page 0.
    const page = this.getPage();
    const { hidePinned } = this.state;
    // Loading
    this.setState({ posts: null });
    const posts = await Api.getSectionPosts(this.props.section.path_name, page, {postCount: POST_COUNT, sortBy: sort, hidePinned, prefix, author});
    if (this.getPage() - 1 !== posts.page) {
      // The API returned a different page than requested.
      // This happens when a page that doesn't exist (e.g. a page higher than the total number of pages) is requested.
      // Set the website's page back to whatever was returned.
      this.setPage(posts.page + 1);
    }
    posts.posts.forEach((post) => {
      post.prefixes.forEach((prefix) => {
        // White is invisible against the white background, but black will also contrast
        // with any color white does (other than black, which no prefixes use).
        if (prefix.bg_color === "white") prefix.bg_color = "black";
      });
      Object.defineProperty(post, "downloading", {
        get: function() {
          return this.files.length > 0 && !this.files.every((file) => file.hasOwnProperty("bufferedDownload"));
        }
      });
      /*post.files.forEach((file) => {
        Api.download(file).then((buffer) => {
          file.bufferedDownload = buffer;
        });
      });*/
    });
    this.setState({ posts });

    const start = Date.now();
    /*posts.posts.forEach((post) => {
      post.files.forEach((file) => {
        Api.download(file).then((buffer) => {
          file.bufferedDownload = buffer;
          if (posts.posts.every((post) => !post.downloading)) console.log(`All posts downloaded in ${(Date.now()-start)/1000}s`);
          this.setState({ posts });
        });
      });
    });
    */
  }
  componentDidUpdate(prevProps) {
    if (this.props.location !== prevProps.location) {
      // Location changed; check if query string is the same
      const newQuery = this.getQuery();
      const oldQuery = qs.parse(prevProps.location.search, {ignoreQueryPrefix: true});
      const newParams = this.props.match.params;
      const oldParams = prevProps.match.params;
      if (
        newQuery.sort !== oldQuery.sort ||
        newQuery.prefix !== oldQuery.prefix ||
        newQuery.author !== oldQuery.author ||
        newParams.page !== oldParams.page
      ) {
        // Relevant query parameters have changed. Update posts.
        this.updatePosts();
      }
    }
  }
  componentDidMount() {
    let hidePinned = JSON.parse(localStorage.getItem("hidePinned"));
    if (hidePinned === null) hidePinned = true;
    this.setState({ hidePinned }, () => {
      if (this.props.section !== null) {
        this.updatePosts();
      }
    });
  }
  componentWillUnmount() {
    // Abort fetch
  }
  render() {
    const skeleton = this.props.section === null;
    return (
      <div className="padded w-100 h-100">
        <div className="section py-2 py-md-4 px-0 px-md-4 h-100 d-flex flex-column" style={{"--active-link-after-text": `' of ${this.getTotalPages()}'`}}>
          <Helmet>
            {!skeleton && <title>{this.props.section.name}</title>}
          </Helmet>
          <div className={classNames("section-header mb-3 mx-3 mx-md-0 mt-3 mt-md-0", skeleton && "skeleton")}>
            <h5 className="section-title mb-0" style={skeleton ? {width: "15%"} : {}}>{!skeleton ? this.props.section.name : "\u00a0"}</h5>
            <small style={skeleton ? {display: "inline-block", width: "50%"} : {}}>{!skeleton ? this.props.section.description : "\u00a0"}</small>
          </div>

          <div className="section-outer-tools mb-3 d-flex justify-content-between align-items-center mt-1 mt-md-0 mx-3 mx-md-0">
            <div className="d-flex align-items-center">

              {this.pagination(true, {innerClass: "pagination p-0 m-0 upper"})}
            </div>
            <div className="d-flex justify-content-center align-items-center">
              <Form.Check className="" type="checkbox" label="Hide pinned posts" checked={this.state.hidePinned} onChange={this.updateHidePinned}/>
            </div>
          </div>
          {/*
          <Pagination>
          {
            this.state.posts !== null && (
              Array.from(new Array(this.state.posts.pages)).map((_, i) => <Pagination.Item key={i} active={i === this.getPage()}>{i}</Pagination.Item>)
            )
          }
          </Pagination>
          */}
          {
            !skeleton && (
              <div className="filter-container rounded-top w-100 bg-light d-flex p-2">
                <div className="filter-tag-container flex-grow-1">
                  {
                    this.getQuery().prefix && (
                      <Badge pill
                             className="hover btn border-0 px-3 py-2 d-inline-flex justify-content-center align-items-center badge-primary btn-primary"
                             onClick={this.clearPrefix}>
                        Prefix: {this.parsePrefix().name}
                        <FaTimes className="ml-1"/>
                      </Badge>
                    )
                  }
                  {
                    this.getQuery().author && (
                      <Badge pill
                             className="hover btn border-0 px-3 py-2 d-inline-flex justify-content-center align-items-center badge-primary btn-primary"
                             onClick={this.clearAuthor}>
                        Author: {this.getQuery().author}
                        <FaTimes className="ml-1"/>
                      </Badge>
                    )
                  }
                </div>
                <Form.Control className="sort-select custom-select custom-select-sm w-auto" as="select" onChange={this.updateSort} value={this.getQuery().sort}>
                  {this.SORT_BY.map((option) => <option key={option} value={option}>{option}</option>)}
                </Form.Control>
              </div>
            )
          }
          <div className="post-container flex-grow-1">
            {
              this.state.posts === null ? (
                Array.from(new Array(POST_COUNT)).map((_, i) => <Post skeleton={true} key={i}/>)
              ) : this.state.posts.posts.length === 0 ? (
                <div className="empty-posts w-100 h-100 d-flex justify-content-center align-items-center">
                  <div className="rounded-circle  d-flex justify-content-center align-items-center flex-column" style={{width: "400px", height: "400px"}}>
                    <h5>No posts</h5>
                    <p>No posts meet these criteria.</p>
                  </div>
                </div>
              ) : (
                this.state.posts.posts.map((post) => (
                  <Post post={post}
                        key={post.id}
                        playing={this.state.playing}
                        setPlaying={this.setPlaying}
                        setPaused={this.setPaused}
                        updateAuthor={this.updateAuthor}
                        setPrefix={this.setPrefix}/>
                ))
              )
            }
          </div>
          <div className="d-flex justify-content-center">{this.pagination(false)}</div>
        </div>
      </div>
    )
  }
}
export default withRouter(Section);
