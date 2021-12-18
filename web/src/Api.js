import qs from 'qs';
import { API_URL as BASE_URL, OMIT_UNKNOWN_FILES } from './config.js';

export class Api {
  async getSectionPosts(sectionName, page, query) {
    const { postCount, sortBy, hidePinned, prefix, author } = query;
    page -= 1; // api starts pages at 0
    const queryString = qs.stringify({ posts: postCount, sort_by: sortBy, hide_pinned: hidePinned, prefix_raw_id: prefix, author: author });
    const res = await fetch(`${BASE_URL}/section/${sectionName}/${page}?${queryString}`);
    const posts = await res.json();
    if (OMIT_UNKNOWN_FILES) {
      posts.posts.forEach((post) => {
        post.files = post.files.filter((file) => !file.unknown);
      });
    }
    return posts;
  }
  async download_url(file) {
    const driveRes = await fetch(`${BASE_URL}/download/${file.drive_id}`);
    const driveUrl = await driveRes.json();
    return driveUrl;
    const res = await fetch(driveUrl);
    let blob = await res.blob();
    blob = blob.slice(0, blob.size, "audio/mpeg");
    return blob;
  }
  async getSections() {
    const res = await fetch(`${BASE_URL}/sections`);
    const sections = await res.json();
    // const sections = 5;
    return sections;
  }
  async getPrefixes() {
    const res = await fetch(`${BASE_URL}/prefixes`);
    const prefixes = await res.json();
    return prefixes
  }
  async getInfo(options) {
    const res = await fetch(`${BASE_URL}/info?${qs.stringify(options)}`);
    const info = await res.json();
    return info;
  }
  async updateConfig(options) {
    const data = new FormData();
    Object.entries(options).forEach(([option, value]) => data.append(option, value));
    const res = await fetch(`${BASE_URL}/config`, {
      method: "POST",
      body: data
    });
    return await res.json();
  }
}
// Api.Route("section").Route("10").Route("5").QueryArg()
export default new Api()
