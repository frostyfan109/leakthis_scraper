import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Layout, Button, Menu, Space, Divider, Input } from 'antd';
import { STATIC_URL } from '../config';

const { Header } = Layout;

export function Navbar({sections, searchQuery, setSearchQuery}) {
    const location = useLocation();
    return (
        <Header style={{display: "flex", width: "100%"}}>
            <Link to="/">
                <img
                    src={STATIC_URL + "/logo.png"}
                    width="100px"
                    alt={process.env.REACT_APP_WEBSITE_NAME}
                    />
            </Link>
            <Menu theme="light" mode="horizontal" selectedKeys={[location.pathname]}>
                {
                Object.entries(sections || {}).map(([sectionName, section]) => (
                    <Menu.Item key={section.path}>
                        <Link to={section.path}>{section.name}</Link>
                    </Menu.Item>
                ))
                }
                <Divider type="vertical"/>
                <Menu.Item key="/info">
                    <Link to="/info">Info</Link>
                </Menu.Item>
                <Divider type="vertical"/>
                <Menu.Item key="/drive-info">
                    <Link to="/drive-info">Drive</Link>
                </Menu.Item>
            </Menu>
            <Input
                placeholder="Search"
                value={searchQuery || ""}
                onChange={(e) => setSearchQuery(e.target.value)}/>
        </Header>
    );
}