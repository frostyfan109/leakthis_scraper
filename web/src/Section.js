import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import { Helmet } from 'react-helmet';
import { FaEye, FaComment, FaTimes, FaThumbtack, FaStepForward, FaStepBackward } from 'react-icons/fa';
import { IoPlaySkipForwardSharp, IoPlaySkipBackSharp, IoAlertSharp, IoRepeatSharp, IoDownloadSharp, IoRefreshSharp } from 'react-icons/io5';
import { IoIosPlay as FaPlay, IoIosPause as FaPause } from 'react-icons/io';
import { Link, withRouter, generatePath } from 'react-router-dom';
import { Card, Badge, Form, Button } from 'react-bootstrap';
import { toast } from 'react-toastify';
import Pagination from 'react-js-pagination';
import Draggable from './Draggable';
import { POST_COUNT } from './config.js';
import { QueryParamsPageComponent } from './QueryParams.js';
import { abbrNum, getFileType, FileType, FileSubType } from './common.js';
import Api from './Api.js';
import qs from 'qs';
import JSZip from 'jszip';
import fileDownload from 'js-file-download';
import * as mm from 'music-metadata-browser';
import Skeleton from 'react-loading-skeleton';
import moment from 'moment';
import pluralize from 'pluralize';
import classNames from 'classnames';
import { socket } from './socket';

class Post extends QueryParamsPageComponent {
  constructor(props) {
    super(props);

    this.state = {
      dragging: false,
      // position: {x: 0, y: 0}
    };

    this.dragContainerRef = React.createRef();
    this.dragRef = React.createRef();
  }
  getZipFileNames() {
    const { playing: { zip: { files } } } = this.props;
    // If every file is in a single dir at the top level, then return the contents
    // of the directory without the dir name.
    // I.e. a zip of a directory.
    const topLevelDirs = Object.values(files).filter((file) => {
      const isTopDir = file.name.split("/").length === 2 && file.name.endsWith("/") && file.dir;
      return isTopDir;
    });
    if (topLevelDirs.length === 1) {
      const topLevelDir = topLevelDirs[0];
      // Remove top level dir from files and replace first instance of its name with empty string.
      return Object.values(files).filter((file) => file !== topLevelDir).map((file) => file.name.replace(topLevelDir.name, ""));
    }
    return Object.values(files).map((file) => file.name);
  }
  getProgress() {
    const { playing } = this.props;
    switch (playing.type) {
      case FileType.AUDIO:
        // Safeguard NaN values.
        const current = isNaN(playing.audio.currentTime) ? 0 : playing.audio.currentTime;
        const duration = isNaN(playing.audio.duration) ? 0 : playing.audio.duration;
        // Safeguard indeterminate 0 / 0;
        if (current === 0 && duration === 0) return 0;
        return current / duration;
      default:
        return 1;
    }
    
  }
  getScrubberPosition() {
    if (!this.dragContainerRef.current) return 0;
    else return this.dragContainerRef.current.offsetWidth * this.getProgress(); 
  }
  updateScrubberPosition(x, noSet=false) {
    if (this.props.playing.audio.failed === true || this.props.playing.audio.loading) return;
    // Clamp between 0 and container width;
    // x = Math.min(Math.max(x, 0), this.dragContainerRef.current.offsetWidth);
    x = Math.min(Math.max(x, 0), this.dragContainerRef.current.offsetWidth);

    // Clamp between 0 and 1.
    const newProgress = Math.min(Math.max(x / this.dragContainerRef.current.offsetWidth, 0), 1);
    if (!noSet) {
      this.props.playing.audio.currentTime = (this.props.playing.audio.duration * newProgress).toString();
    }
    // console.log(this.props.playing.audio.currentTime, this.props.playing.audio.duration * newProgress)
    // console.log(x, this.props.playing.audio.duration * newProgress);
    // this.setState({ position : {x, y: 0} });
    // console.log(this.props.playing.audio.duration * newProgress);
    this.setState({});
  }
  startScrubbing(x) {
    this.props.playing.audio.wasPaused = this.props.playing.audio.paused;
    this.props.playing.audio.pause();
    this.setState({ dragging : true });
    // this.updateScrubberPosition(x - this.dragContainerRef.current.getBoundingClientRect().left);
  }
  stopScrubbing(x) {
    const { playing } = this.props;
    if (!playing.audio.wasPaused) playing.audio.play();
    delete playing.audio.wasPaused;
    this.setState({ dragging : false });
    // this.updateScrubberPosition(x - this.dragContainerRef.current.getBoundingClientRect().left);
  }
  getPlayCircleImage() {
    switch (this.props.playing.type) {
      case FileType.AUDIO:
        const fillColor = "rgb(188, 189, 191)";
        let startDeg = 0;
        let endDeg = this.getProgress() * 360;
        let color = fillColor;
        if (endDeg > 180) {
          endDeg -= 180;
          color = "var(--primary)";
        } 
        return `
          linear-gradient(${endDeg + 90}deg, transparent 50%, ${color} 50%),
          linear-gradient(${startDeg + 90}deg, ${fillColor} 50%, transparent 50%)
        `;
      default:
        return ``;
    }
    
  }
  formatProgress(time) {
    if (isNaN(time)) time = 0;
    // For some reason, moment-duration-format rounds when formatting which makes no sense
    // and messes up the manual formatting going off of duration.asSeconds/duration.asMinutes which are unrounded.
    const duration = moment.duration(Math.floor(time) * 1000);
    const formatted = duration.format("H:m:ss");
    // It chops off the "0:0" in "0:0s" if there are less than 10 seconds.
    if (duration.asSeconds() < 10) return `0:0${formatted}`
    // It chops the minute part off the "0:" in "0:ss" if there is less than 1 minute.
    if (duration.asMinutes() < 1) return `0:${formatted}`;
    return formatted;
  }
  render() {
    let { post, skeleton, setPlaying, setPaused, unpausePlaying, playing: playingObj } = this.props;
    if (skeleton) {
      post = {
        prefixes: [],
        files: []
      };
      //
      setPlaying = () => {};
      setPaused = () => {};
      unpausePlaying = () => {};
    }
    let playing = false;
    let file = null;
    let IS_AUDIO = false;
    let IS_ZIP = false;
    
    let IS_PAUSED = false;
    let IS_LOADING = false;
    let IS_ERROR = false;
    if (playingObj) {
      playing = post.id === playingObj.post_id;
      // this.state.dragging && console.log(playingObj.audio.wasPaused);
      file = playingObj;

      switch (file.type) {
        case FileType.ZIP: {
          IS_ZIP = true;
          IS_PAUSED = true;
          IS_LOADING = file.zip.loading;
          IS_ERROR = file.zip.failed;
          break;
        }
        case FileType.AUDIO: {
          IS_AUDIO = true;
          IS_PAUSED = playing && playingObj.audio.paused;
          if (this.state.dragging) IS_PAUSED = playingObj.audio.wasPaused;
          IS_LOADING = file.audio.loading;
          IS_ERROR = file.audio.failed;
          break;
        }
        default: {
          IS_PAUSED = true;
          break; 
        }
      }

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
            {post.files.length !== 0 && <div className={
                   classNames(
                     "d-flex justify-content-center align-items-center rounded-circle outer-player-container",
                     playing && "play",
                     IS_PAUSED && "paused",
                     playing ? "mr-3" : "mr-2",
                     playing && (IS_ERROR ? "error" : IS_LOADING ? "spinner-border text-primary" : "")
                   )
                 }
                 style={{
                   width: "46px",
                   height: "46px",
                   backgroundImage: playing && !IS_LOADING ? this.getPlayCircleImage() : undefined,
                   backgroundColor: playing && IS_LOADING ? "rgb(188, 189, 191)" : ""
                 }}
                 onClick={() => !playing ? setPlaying(post, 0) : (IS_PAUSED ? unpausePlaying()  : setPaused())}>
              <div className="rounded-circle inner-player-container">
                {
                  (playing && IS_ERROR) ? (
                    <IoAlertSharp className="audio-player error text-danger"/>
                  ) : (playing && IS_LOADING) ? (
                    null
                  ) : (playing && !IS_PAUSED) ? (
                    <FaPause className="audio-player"/>
                  ) : (
                    <FaPlay className={classNames("audio-player", playing && this.getProgress() === 1 && "complete")}/>
                  )
                }
              </div>
            </div>
            }
            <div className="media-body mr-3 mr-md-0">
              <h6 className="post-header d-inline">
                {
                  post.prefixes.map((prefix) => (
                    <React.Fragment key={prefix.id}>
                    <a href="javascript:void(0);" className="d-inline-block" onClick={() => !skeleton && this.props.setPrefix(prefix.id)}>
                      <span className="d-flex justify-content-center align-items-center">
                        {/* Badge has 3px margin-y on default. Add 2px to margin-top so adjust for text alignment. */}
                        <Badge style={{color: prefix.text_color, backgroundColor: prefix.bg_color, fontSize: ".75rem", paddingTop: "5px"}}>{prefix.name}</Badge>
                      </span>
                    </a>
                    &nbsp;
                    </React.Fragment>
                  ))
                }
                {
                  skeleton
                    ? <div className="d-inline-block w-100"></div>
                    : <a href="javascript:void(0);" className="text-body d-inline">{post.title}</a>
                }
              </h6>
              {/*<p className="text-secondary">
                {post.body}
              </p>*/}
              <p className={classNames("text-muted mb-0 post-footer", skeleton && "mt-1")}>
                {
                  skeleton ? (
                    <>
                    <span>{"\u00a0".repeat(20)}</span>
                    <span>{"\u00a0".repeat(25)}</span>
                    <span>{"\u00a0".repeat(15)}</span>
                    </>
                  ) : (
                    <>
                    <a href="javascript:void(0);" className="text-muted" onClick={() => this.props.updateAuthor(post.created_by)}>{post.created_by}</a>
                    <span className="text-secondary">
                      &nbsp;&bull;&nbsp;{moment(post.created*1000).fromNow()}
                      &nbsp;&bull;&nbsp;{pluralize("file", post.files.length, true)}
                    </span>
                    </>
                  )
                }
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
              <div className={classNames("audio-player-info d-flex align-items-center mb-1", (IS_ERROR || IS_LOADING) && "text-disabled")}>
                {file.file_name} {post.files.length > 1 && `(${this.props.getCurrentTrackPosition() + 1} of ${post.files.length})`}
              </div>
              <div className="bottom-controls d-flex align-items-center">
                <IoRepeatSharp className={classNames("audio-repeat ml-2", IS_ERROR && "disabled", this.props.repeatEnabled && "enabled")}
                               onClick={() => this.props.toggleRepeat()}/>
                <IoPlaySkipBackSharp className={classNames("audio-skip ml-2", !this.props.canSkipBackward() && "disabled")} onClick={() => this.props.canSkipBackward() && this.props.skipTrack(-1)}/>
                {IS_AUDIO ? (
                  <>
                  <span className="progress-time progress-time-elapsed small">{this.formatProgress(file.audio.currentTime)}</span>
                  <div className="audio-progress-outer flex-grow-1 d-flex flex-column justify-content-center"
                      ref={this.dragContainerRef}
                      onMouseDown={(e) => {
                        //  e.preventDefault();
                        this.updateScrubberPosition(e.nativeEvent.offsetX);
                        setTimeout(() => {
                        this.dragRef.current._onMouseDown({
                          stopPropagation: e.stopPropagation,
                          preventDefault: e.preventDefault,
                          button: e.button,
                          pageX: e.pageX,
                          pageY: e.pageY
                        });
                        }, 0);
                      }}>
                    <div className="audio-progress-inner rounded">
                      <div className="audio-progress-bar rounded" style={{"width": this.getProgress() * 100 + "%"}}/>
                    </div>
                    <Draggable x={this.getScrubberPosition()}
                              y={0}
                              ref={this.dragRef}
                              onStart={(e, x, y) => {e.stopPropagation();this.startScrubbing(x)}}
                              onEnd={(e, x, y) => {e.stopPropagation();this.stopScrubbing(x)}}
                              onMove={(e, x, y) => {
                                e.stopPropagation();
                                if (!this.state.dragging) return;
                                this.updateScrubberPosition(x - this.dragContainerRef.current.getBoundingClientRect().left);
                              }}>
                      <div className={classNames("audio-progress-scrubber", this.state.dragging && "dragging")}
                          style={{display: IS_LOADING || IS_ERROR ? "none" : undefined}}/>
                    </Draggable>
                  </div>
                  <span className="progress-time progress-time-left small">{this.formatProgress(file.audio.duration)}</span>
                  </>
                ) : IS_ZIP ? (
                  <div className="flex-grow-1 px-2 text-center" style={{textOverflow: "ellipsis", overflow: "hidden", flexBasis: 0}}>
                    {
                    IS_ERROR ? (
                      <span className="text-danger"></span>
                    ) : IS_LOADING ? (
                      <span className=""></span>
                    ) : (
                      <small className="text-nowrap">
                        {this.getZipFileNames().join(", ")}
                      </small>
                    )
                    }
                  </div>
                ) : (
                  <div className="flex-grow-1"/>
                )}
                <IoPlaySkipForwardSharp className={classNames("audio-skip mr-2", !this.props.canSkipForward() && "disabled")} onClick={() => this.props.canSkipForward() && this.props.skipTrack(1)}/>
                <IoDownloadSharp className={classNames("audio-download mr-2")}
                                 onClick={() => this.props.downloadPlaying()}/>
                {IS_ERROR && (
                  <IoRefreshSharp className="audio-reload mr-2 text-primary"
                                  onClick={() => this.props.reloadPlaying()}/>
                )}
              </div>
            </div>
          )
        }
      </Card>
    );
  }
}

class Section extends QueryParamsPageComponent {
  constructor(props) {
    super(props);

    this.state = {
      posts: null,
      pages: null,
      hidePinned: false,
      playing: null,
      repeat: false
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
    this.canSkipBackward = this.canSkipBackward.bind(this);
    this.canSkipForward = this.canSkipForward.bind(this);
    this.skipTrack = this.skipTrack.bind(this);
    this.unpausePlaying = this.unpausePlaying.bind(this);
    this.getCurrentTrackPosition = this.getCurrentTrackPosition.bind(this);
    this.toggleRepeat = this.toggleRepeat.bind(this);
    this.downloadPlaying = this.downloadPlaying.bind(this);
    this.reloadPlaying = this.reloadPlaying.bind(this);

    this.SORT_BY = [
      "latest",
      "popular",
      "active"
    ];
    // Used when query param is not specified.
    this.SORT_BY_DEFAULT = "latest"
  }
  skeleton() {
    return this.props.section === null;
  }
  toggleRepeat() {
    this.setState({ repeat: !this.state.repeat });
  }
  async preparePost(post) {
    for (let j=0; j<post.files.length; j++) {
      const file = post.files[j];
      file.src = await Api.getDownloadUrl(file);
      this.prepareFile(file);
    }
  }
  async prepareFile(file) {
    [file.type, file.subType] = getFileType(file.mime_type);

    const updatePlayingState = () => {
      if (this.state.playing === file) this.setState({ playing : file });
    }

    switch (file.type) {
      case FileType.ZIP: {
        const zip = new JSZip();
        zip.loading = true;
        const loadingFailed = (err) => {
          console.log(err);
          zip.failed = true;
          updatePlayingState();
        }
        fetch(file.src).then((res) => res.arrayBuffer()).then((buf) => {
          zip.loadAsync(buf)
            .then((data) => {
              zip.loading = false; 
              updatePlayingState();
            })
            .catch(loadingFailed);
        }).catch(loadingFailed);
        file.zip = zip;
        break;
      }
      case FileType.AUDIO: {
        try {
          file.audio = new Audio();
          file.audio.loading = true;
          file.audio._abortSignals = {
            downloadController: new AbortController(),
            conversionController: new AbortController()
          };
          const res = await fetch(file.src, {
            signal: file.audio._abortSignals.downloadController.signal
          });
          const audioBlob = await res.blob();
          if (file.subType === FileSubType.M4A) {
            try {
              const mp3Blob = await Api.convertAudio("m4a", "mp3", audioBlob, {
                signal: file.audio._abortSignals.conversionController.signal
              });
              file.audio.src = URL.createObjectURL(mp3Blob);
            } catch (e) {
              // Conversion API probably not configured/running.
              console.error(e);
              file.audio.failed = true;
            }
          } else {
            file.audio.src = URL.createObjectURL(audioBlob);
          }
          
          file.audio.addEventListener("timeupdate", () => {
            // Tracking for scrubbing/etc.
            if (file.audio.currentTime === file.audio.duration) {
              if (file.audio._pausedBeforeEnd === undefined) file.audio._pausedBeforeEnd = file.audio.prevFilePaused;
              delete file.audio.prevFilePaused;
            }
            file.audio.prevFilePaused = file.audio.wasPaused !== undefined ? file.audio.wasPaused : file.audio.paused;
            updatePlayingState();
          });
          file.audio.addEventListener("loadedmetadata", () => {
            file.audio.loading = false;
            updatePlayingState();
          });
          file.audio.addEventListener("error", (e) => {
            if (file.audio.error.code === MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) {
              // 
            }
            file.audio.failed = true;
            updatePlayingState();
          });
          file.audio.addEventListener("ended", () => {
            // Autoplay next file.
            const pausedBeforeEnd = file.audio._pausedBeforeEnd;
            delete file.audio._pausedBeforeEnd;
            // If the file ended while "playing", autoplay next, unless repeat turned on.
            if (this.state.playing === file && pausedBeforeEnd === false) {
              if (this.state.repeat) {
                this.resetPlaying();
                file.audio.play();
              } else {
                if (this.canSkipForward()) this.skipTrack(1);
              }
            } else {
              // If the file ended while paused, it had to be scrubbed to the end (while paused).
              // Even though scrubbing will set currentTime === duration, the "ended" event won't
              // trigger until the user presses play.
              // Don't loop for single files.
              if (this.state.repeat) {
                file.audio.currentTime = 0;
                file.audio.play();
              }
            }
            updatePlayingState();
          });
        } catch (e) {
          if (e.name !== "AbortError") throw e;
        }
        break;
      }
      default: {
        break;
      }
    }
    
  }
  reloadPlaying() {
    this.prepareFile(this.state.playing);
    this.setState({ playing : this.state.playing });
  }
  downloadPlaying() {
    const a = document.createElement("a");
    a.href = this.state.playing.src;
    a.download = true;
    a.click();
  }
  canSkipBackward() {
    try {
      return this.getCurrentTrackPosition() > 0;
    } catch {}
  }
  canSkipForward() {
    try {
      return this.getCurrentTrackPosition() < this.getPlayingPost().files.length - 1;
    } catch {}
  }
  skipTrack(pos) {
    const post = this.getPlayingPost();
    this.setPlaying(post, this.getCurrentTrackPosition() + pos);
  }
  getCurrentTrackPosition() {
    try {
      const files = this.getPlayingPost().files;
      return files.indexOf(this.state.playing);
    } catch {}
  }
  getPlayingPost() {
    return this.state.posts.posts.find((post) => post.files.some((file) => file === this.state.playing));
  }
  setPlaying(post, filePos=0) {
    // if (this.state.paused && post.id === this.state.playing) {
    /*
    if (this.paused() && post.id === this.state.playing.id) {
    const { playing } = this.state;
    playing.paused = false;
    playing.audio.play();
    this.setState({ playing });
    }
    else {
    this.state.playing && this.state.playing.audio.play();
    this.setState({ playing: {
    id: post.id,
    file: post.files[0],
    paused: false,
    audio
    }});
    }
    */
    if (post === null) {
      if (this.state.playing) this.resetPlaying();
      this.setState({ playing : null });
    } else {
      this.setFilePlaying(post.files[filePos]);
    }
  }
  unpausePlaying() {
    switch (this.state.playing.type) {
      case FileType.AUDIO:
        if (this.state.playing.audio.currentTime === this.state.playing.audio.duration) this.resetPlaying(); 
        this.state.playing.audio.play();
        break;
    }
  }
  setFilePlaying(file) {
    const { playing } = this.state;
    if (playing && file !== playing) {
      // Only reset the audio if changing audio files.
      // Otherwise, just unpause it.
      this.resetPlaying();
    }
    if (file.type === FileType.AUDIO) file.audio.play();
    this.setState({ playing : file });
  }
  resetPlaying() {
    switch (this.state.playing.type) {
      case FileType.AUDIO: {
        this.state.playing.audio.pause();
        this.state.playing.audio.currentTime = 0;
        break;
      }
    }
  }
  paused() {
    return this.state.playing.audio.paused;
  }
  setPaused() {
    if (this.state.playing.audio.loading || this.state.playing.audio.failed) return;
    this.state.playing.audio.pause();
    this.setState({ playing: this.state.playing });
    /*
    const { playing } = this.state;
    playing.paused = true;
    playing.audio.pause();
    this.setState({ playing });
    */
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
  getQSPrefixes() {
    const prefixes = this.getQuery().prefix;
    // There are no prefixes in the QS.
    if (typeof prefixes === "undefined") return [];
    // There is a single prefix in the QS.
    else if (!Array.isArray(prefixes)) return [prefixes];
    // There are multiple prefixes in the QS.
    else return prefixes
  }
  setPrefix(prefix) {
    const oldPrefixes = this.getQSPrefixes();
    // Add prefix if not there, remove if there.
    const prefixes = oldPrefixes.indexOf(prefix.toString()) === -1
      ? oldPrefixes.concat(prefix)
      : oldPrefixes.filter((p) => p !== prefix.toString());
    this.setQueryParams({"prefix": prefixes });
  }
  clearPrefix(prefix) {
    this.setQueryParams({"prefix": this.getQSPrefixes().filter((i) => i !== prefix.toString())});
  }
  // parsePrefix() {
  //   return this.getPrefix({id: parseInt(this.getQuery().prefix)});
  // }
  parsePrefixes() {
    return this.getQSPrefixes().map((prefixId) => this.getPrefix({id: parseInt(prefixId)}));
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
  _sectionPostsFetchData() {
    const queryParams = qs.parse(this.props.location.search, {ignoreQueryPrefix: true});
    const sort = queryParams.sort;
    const prefix = queryParams.prefix;
    const author = queryParams.author;
    const query = this.props.searchQuery;
    // Page parameter is optional. If it is omitted, it is page 0.
    const page = this.getPage();
    const { hidePinned } = this.state;
    const data = {
      postCount: POST_COUNT,
      sortBy: sort,
      hidePinned,
      prefix,
      author,
      query
    };
    return { page, data };
  }
  async updatePosts() {
    if (this.skeleton()) return;
    console.log("Updating posts");
    const { page, data } = this._sectionPostsFetchData();
    // Loading
    const oldPosts = this.state.posts;
    oldPosts && oldPosts.posts.forEach((post) => {
      this.cleanupFiles(post);
    })
    this.setState({ posts: null });
    
    const controller = this.props.getUpdatePostsAborter();
    try {
      let posts = await Api.getSectionPosts(this.props.section.path_name, page, data, {
        signal: controller.signal
      });
      if (this.getPage() - 1 !== posts.page) {
        // The API returned a different page than requested.
        // This happens when a page that doesn't exist (e.g. a page higher than the total number of pages) is requested.
        // Set the website's page back to whatever was returned.
        this.setPage(posts.page + 1);
      }
      for (let i=0; i<posts.posts.length; i++) {
        const post = posts.posts[i];
        await this.preparePost(post);
      }
      this.setPlaying(null);
      this.setState({ posts })
    } catch (e) {
      if (e.name !== "AbortError") throw e;
    }
  }
  componentDidUpdate(prevProps) {
    const searchChanged = this.props.searchQuery !== prevProps.searchQuery;
    const sectionChanged = this.props.section !== prevProps.section;
    const prefixesChanged = JSON.stringify(this.props.prefixes) !== JSON.stringify(prevProps.prefixes);
    // Location changed; check if query string is the same
    const newQuery = this.getQuery();
    const oldQuery = qs.parse(prevProps.location.search, {ignoreQueryPrefix: true});
    const newParams = this.props.match.params;
    const oldParams = prevProps.match.params;
    if (
      newQuery.sort !== oldQuery.sort ||
      JSON.stringify(newQuery.prefix) !== JSON.stringify(oldQuery.prefix) ||
      newQuery.author !== oldQuery.author ||
      // newQuery.query !== oldQuery.query ||
      newParams.page !== oldParams.page ||
      searchChanged ||
      sectionChanged ||
      prefixesChanged
    ) {
      // Relevant query parameters have changed. Update posts.
      this.updatePosts();
    }
  }
  cleanupFiles(post) {
    post.files.forEach((file) => {
      if (file.audio) {
        file.audio.pause();
        // Cancel fetch downloads to lighten server load.
        Object.values(file.audio._abortSignals).forEach((controller) => {
          controller.abort();
        });
        // Browser will just ignore if src isn't an object URL.
        URL.revokeObjectURL(file.audio.src);
      }
    });
  }
  componentDidMount() {
    let hidePinned = JSON.parse(localStorage.getItem("hidePinned"));
    if (hidePinned === null) hidePinned = true;
    this.setState({ hidePinned }, () => {
      if (this.props.section !== null) {
        this.updatePosts();
      }
    });
    socket.on("post_created", async (post) => {
      // Only bother if the post was created in the last 5 minutes. Don't want to flood
      // the UI with notifications when the scraper starts up after a bit and archives
      // a bunch of posts at once
      const minutesAgoCreated = (Date.now() - post.created * 1000) / (1000 * 60);
      if (minutesAgoCreated > 5) {
        console.log(`Skipping post_created for ${post.id} (created ${Math.floor(minutesAgoCreated)} minutes ago).`);
      }
      // Only update if the new post is in this section.
      if (this.props.section?.id === post.section_id) {
        // Don't want to refresh the entire page of posts when a new post is made for the following reasons:
        // - The logic gets even more unnecessarily overcomplicated
        // - If the user is listening to the last post on the page, and a new post is made, the last post will disappear
        //   (it gets bumped to the next page). This is definitely not desirable.
        // Instead, just add the post to the start of the page (which could theoretically overflow if left open indefinitely)
        // but is a much better solution that the former.
        const { page, data } = this._sectionPostsFetchData();
        // Don't both with an abort controller, since it is a niche request with very minimal server load.
        const posts = await Api.getSectionPosts(this.props.section.path_name, page, data);
        if (posts.posts.find((pagePost) => pagePost.id === post.id)) {
          await this.preparePost(post);
          if (this.state.posts === null) return;
          this.state.posts.posts = [post, ...this.state.posts.posts];
          this.setState({ posts : this.state.posts });
        }
        toast(<>
          <h6>New post in {this.props.section.name}</h6>
          <hr className="mt-1 mb-2"/>
          {post.prefixes.map((prefix) => (
            <Badge className="mr-1" style={{color: prefix.text_color, backgroundColor: prefix.bg_color, fontSize: ".75rem", paddingTop: "5px"}}>
              {prefix.name}
            </Badge>
          ))}
          <span style={{color: "black"}}>{post.title}</span>
          <br/>
          <small className="text-muted">{post.created_by} &bull; {pluralize("file", post.files.length, true)}</small>
        </>);
      }
    });
  }
  componentWillUnmount() {
    this.state.posts && this.state.posts.posts.forEach((post) => this.cleanupFiles(post));
  }
  render() {
    const skeleton = this.skeleton();
    const noPosts = this.state.posts !== null && this.state.posts.posts.length === 0;
    return (
      <div className="padded w-100">
        <div className={classNames("section py-2 py-md-4 px-0 px-md-4 h-100 d-flex flex-column", skeleton && "skeleton")}
             style={{"--active-link-after-text": `' of ${this.getTotalPages()}'`}}>
          <Helmet>
            {!skeleton && <title>{this.props.section.name}</title>}
          </Helmet>
          <div className="section-header mb-3 mx-3 mx-md-0 mt-3 mt-md-0">
            <div><h5 className="section-title mb-0 d-inline" style={{wordBreak: "break-word"}}>{!skeleton ? this.props.section.name : "\u00a0".repeat(30)}</h5></div>
            <div><small className="text-wrap" style={{wordBreak: "break-word"}}>{!skeleton ? this.props.section.description : "\u00a0".repeat(200)}</small></div>
          </div>

          <div className="section-search mb-3 mt-1 mt-md-0 mx-3 mx-md-0 border-top pt-3" style={{display: !this.props.searchQuery ? "none" : undefined }}>
            <div><h6 className="d-inline mb-0 text-wrap" style={{wordBreak: "break-word"}}>{!skeleton ? `Search results for: ${this.props.searchQuery}` : "\u00a0".repeat(60)}</h6></div>
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
              <div className="filter-container rounded-top w-100 bg-light p-2 border border-bottom-0" style={{display: noPosts ? "none" : "flex"}}>
                <div className="filter-tag-container flex-grow-1">
                  {
                    this.parsePrefixes().map((prefix) => (
                      <Badge pill
                             className="hover btn border-0 px-3 py-2 d-inline-flex justify-content-center align-items-center badge-primary btn-primary"
                             onClick={() => this.clearPrefix(prefix.id)}
                             key={prefix.id}>
                        Prefix: {prefix.name}
                        <FaTimes className="ml-1"/>
                      </Badge>
                    ))
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
                <Form.Control className="sort-select custom-select custom-select-sm w-auto" as="select" onChange={this.updateSort} value={this.getQuery().sort || this.SORT_BY_DEFAULT}>
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
                        setPrefix={this.setPrefix}
                        canSkipBackward={this.canSkipBackward}
                        canSkipForward={this.canSkipForward}
                        skipTrack={this.skipTrack}
                        unpausePlaying={this.unpausePlaying}
                        getCurrentTrackPosition={this.getCurrentTrackPosition}
                        repeatEnabled={this.state.repeat}
                        toggleRepeat={this.toggleRepeat}
                        downloadPlaying={this.downloadPlaying}
                        reloadPlaying={this.reloadPlaying}/>
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