import qs from 'qs';
import { API_URL as BASE_URL, CONVERSION_API_URL as CONVERSION_BASE_URL, OMIT_UNKNOWN_FILES } from './config.js';

export class Api {
  async getSectionPosts(sectionName, page, query, fetchOptions={}) {
    const { postCount, sortBy, hidePinned, hideDeleted, prefix, author, query: searchQuery } = query;
    page -= 1; // api starts pages at 0
    const queryString = qs.stringify(
      { posts: postCount, sort_by: sortBy, hide_pinned: hidePinned, hide_deleted: hideDeleted, prefix_raw_id: prefix, author, query: searchQuery },
      { arrayFormat: "repeat" }
    );
    const res = await fetch(`${BASE_URL}/section/${sectionName}/${page}?${queryString}`, fetchOptions);
    const posts = await res.json();
    if (OMIT_UNKNOWN_FILES) {
      posts.posts.forEach((post) => {
        post.files = post.files.filter((file) => !file.unknown);
      });
    }
    return posts;
  }
  /*
  async getDownloadUrl(file) {
    const driveRes = await fetch(`${BASE_URL}/download/${file.drive_id}`);
    const driveUrl = await driveRes.json();
    return driveUrl;
    const res = await fetch(driveUrl);
    let blob = await res.blob();
    blob = blob.slice(0, blob.size, "audio/mpeg");
    return blob;
  }
  */
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
  async getDriveFiles(projectId, page, perPage, searchQuery, fetchOptions={}) {
    if (searchQuery === "") searchQuery = undefined;
    const res = await fetch(`${BASE_URL}/drive_files/${projectId}/${page}?${qs.stringify({ files: perPage, query: searchQuery })}`, fetchOptions);
    const files = await res.json();
    return files;
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
  async searchUsers(query, limit=20) {
    const res = await fetch(`${BASE_URL}/users/${query}?${qs.stringify({ limit })}`);
    const users = await res.json();
    return users;
  }
  async getDownloadUrl(file) {
    return `${BASE_URL}/download/${file.id}`;
  }
  async convertAudio(inFilename, outFilename, fileBlob, fetchOptions) {
    const formData = new FormData();
    formData.append("file", fileBlob);
    const res = await fetch(`${CONVERSION_BASE_URL}/convert_audio/${inFilename}/${outFilename}`, {
      method: "POST",
      body: formData,
      ...fetchOptions
    });
    return await res.blob();
  }
  /*
  async getDownloadUrl(file) {
    const res = await fetch(`${BASE_URL}/download_url/${file.id}`);
    return await res.json();
  }
  */
}
export default new Api()
