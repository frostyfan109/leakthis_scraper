import React, { Component } from 'react';
import { withRouter, generatePath } from 'react-router-dom';
import { scrollToTop } from './util';

export default class QueryParamsComponent extends Component {
  @scrollToTop()
  setQueryParams(location: any, params: any) {
    const search = new URLSearchParams(location.search);
    Object.keys(params).forEach((key) => {
      if (params[key] === undefined) {
        search.delete(key);
      } else {
        if (Array.isArray(params[key])) {
          search.delete(key);
          params[key].forEach((value: any) => {
            search.append(key, value);
          });
        } else {
          search.set(key, params[key]);
        }
      }
    });
    return "?" + search.toString();
  }
}

export class QueryParamsPageComponent extends QueryParamsComponent {
  @scrollToTop()
  foobar() {}
  @scrollToTop()
  setPage(page: any, search: any) {
    const props = this.props as any;
    // console.log(this.props.match.path);
    // console.log(generatePath(this.props.match.path, {page}), search)
    props.history.push({
      pathname: generatePath(props.match.path, {page}),
      search: search || props.location.search
    });
  }
}