import React, { Component } from 'react';
import { withRouter, generatePath } from 'react-router-dom';


export default class QueryParamsComponent extends Component {
    setQueryParams(location, params) {
      const search = new URLSearchParams(location.search);
      Object.keys(params).forEach((key) => {
        if (params[key] === undefined) {
          search.delete(key);
        } else {
          if (Array.isArray(params[key])) {
            search.delete(key);
            params[key].forEach((value) => {
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
  setPage(page, search) {
    // console.log(this.props.match.path);
    // console.log(generatePath(this.props.match.path, {page}), search)
    this.props.history.push({
      pathname: generatePath(this.props.match.path, {page}),
      search: search || this.props.location.search
    });
  }
}