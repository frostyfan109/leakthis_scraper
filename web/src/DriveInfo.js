import React, { useState, useMemo, useEffect } from 'react';
import { Card, Button, Tab, Nav } from 'react-bootstrap';
import { FaFileArchive, FaFile } from 'react-icons/fa';
import moment from 'moment';
import prettyBytes from 'pretty-bytes';
import Api from './Api';
import Loading from './Loading';

export default function DriveInfo({ info }) {
    const [projectId, setProjectId] = useState(null);
    const loading = projectId === null;
    useEffect(() => {
        if (projectId === null && info !== null) setProjectId(Object.keys(info.status.account_info.drive)[0]);
    }, [info]);

    return (
        <div className="py-4 px-4 w-100 h-100">
            {loading ? (
                <div className="h-100 w-100 d-flex justify-content-center align-items-center">
                    <Loading/>
                </div>
            ) : (
                <div className="d-flex h-100 align-items-start">
                    <Tab.Container activeKey={projectId} className="h-100">
                        <Nav variant="pills" className="flex-column text-nowrap" style={{position: "sticky", top: "24px"}}>
                            <h5 className="navbar-brand">Project</h5>
                            {
                                Object.keys(info.status.account_info.drive).map((id) => (
                                    <Nav.Item key={id}>
                                        <Nav.Link eventKey={id} onClick={() => setProjectId(id)}>{id}</Nav.Link>
                                    </Nav.Item>
                                ))
                            }
                        </Nav>
                        <Tab.Content className="pl-3 flex-grow-1 h-100">
                            {
                                Object.keys(info.status.account_info.drive).map((id) => (
                                    <Tab.Pane eventKey={id} className="h-100" key={id}>
                                        <DriveFiles projectId={id}/>
                                    </Tab.Pane>
                                ))
                            }
                        </Tab.Content>
                    </Tab.Container>
                </div>
            )}
        </div>
    );
}

function DriveFiles({ projectId }) {
    const [page, setPage] = useState(0);
    const [perPage, setPerPage] = useState(50);
    const [loadingFiles, setLoadingFiles] = useState(false);
    const [files, setFiles] = useState([]);

    const activeFiles = useMemo(() => {
        return files.reduce((acc, cur) => {
            const dupe = acc.filter((obj) => obj.page === cur.page && obj.per_page === cur.per_page).length > 0;
            if (cur.per_page === perPage && !dupe) acc.push(cur);
            return acc;
        }, []).flatMap((obj) => obj.files);
    }, [perPage, files]);

    useEffect(async () => {
        if (files.find((obj) => obj.page === page && obj.perPage === perPage) === undefined) {
            setLoadingFiles(true);
            const newFiles = await Api.getDriveFiles(projectId, page, perPage);
            setFiles([
                ...files,
                newFiles
            ]);
            setLoadingFiles(false);
        }
    }, [page]);

    const loadNextPage = () => {
        setPage(page + 1);
    }
    return (
        <div className="drive-files h-100">
            {
                files.length === 0 ? (
                    <div className="d-flex justify-content-center align-items-center h-100">
                        <Loading/>
                    </div>
                ) : (
                    <>
                    <div style={{
                        display:"grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                        gridAutoRows: "auto",
                        gap: "20px",
                        wordBreak: "break-all"
                    }}>
                        {
                            activeFiles.map((file) => (
                                <FileCard file={file} key={file.id}/>
                            ))
                        }
                    </div>
                    <div className="d-flex justify-content-center mt-3">
                        {
                            loadingFiles ? (
                                <Loading/>
                            ) : (
                                <Button variant="outline-primary" onClick={loadNextPage}>Load more</Button>
                            )
                        }
                    </div>
                    </>
                )
            }
            
        </div>
    );
}

const FileType = Object.freeze({
    ZIP: 0,
    AUDIO: 1,
    VIDEO: 2,
    UNKNOWN: 3
});

function FileCard({ file }) {
    let type;
    const mainType = file.mimeType.split("/")[0];
    if (file.mimeType === "application/zip") type = FileType.ZIP;
    else if (mainType === "audio") type = FileType.AUDIO;
    else if (mainType === "video") type = FileType.VIDEO;
    else type = FileType.UNKNOWN;

    const cardImage = () => {
        switch (type) {
            case FileType.ZIP:
                return <FaFileArchive className="card-variant-top my-4" style={{width: "100%", fontSize: "106.66667px"}}/>;
            case FileType.AUDIO:
                return <Card.Img variant="top" src={process.env.PUBLIC_URL + "/music.png"} className="my-4" />;
            case FileType.VIDEO:
                return (
                    <video className="w-100 card-variant-top my-4">
                        <source src={file.webContentLink} type={file.mimeType}/>
                    </video>
                );
            case FileType.UNKNOWN:
            default:
                return <FaFile className="card-variant-top my-4" style={{width: "100%", fontSize: "106.66667px"}}/>;
        };
    }
    const cardEmbed = () => {
        switch (type) {
            case FileType.ZIP:
                return (
                    // <iframe className="w-100" src={file.embedLink} allow="autoplay"/>
                    <a href={file.webContentLink} download>Download</a>
                );
            case FileType.AUDIO:
                return (
                    <audio controls className="w-100">
                        <source src={file.webContentLink} type={file.mimeType}/>
                    </audio>
                );
            case FileType.VIDEO:
            case FileType.UNKNOWN:
            default:
                return null;
        }
    }
    
    return (
        <Card style={{height: "min-content", textAlign: "center"}}>
            {cardImage()}
            <Card.Body className="pt-0">
                <Card.Title>{file.title}</Card.Title>
                <Card.Subtitle className="mb-3 text-muted">{file.id}</Card.Subtitle>
                <Card.Text className="mb-0">Size: {prettyBytes(parseInt(file.fileSize)).replace(" ", "")}</Card.Text>
                <Card.Text>Created: {moment(file.createdDate).fromNow()}</Card.Text>
                {cardEmbed()}
            </Card.Body>
        </Card>
    );
}