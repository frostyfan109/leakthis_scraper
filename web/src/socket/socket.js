import io from 'socket.io-client';
import { API_URL } from '../config.js';

export const socket = io(API_URL, { path: "/ws/socket.io" });