import React, { useState, useMemo, useEffect } from 'react';
import { Card, Button, Tab, Nav } from 'react-bootstrap';
import { FaFileArchive, FaFile } from 'react-icons/fa';
import moment from 'moment';
import prettyBytes from 'pretty-bytes';
import Api from './Api';
import Loading from './Loading';

export default function DriveInfo({ info }) {
    const [files, setFiles] = useState({});
    const [page, setPage] = useState(0);
    const [perPage, setPerPage] = useState(50);
    const [projectId, setProjectId] = useState(null);
    const [loadingFiles, setLoadingFiles] = useState(false);
    const loading = useMemo(() => (
        files.length === 0 ||
        info === null ||
        projectId === null
    ), [files, info])
    // const activeFiles = useMemo(() => getActiveFiles(projectId), [files, perPage]);
    const fetchFiles = async () => {
        setLoadingFiles(true);
        const newFiles = await Api.getDriveFiles(projectId, page, perPage);
        const newState = {...files};
        if (newState[projectId] === undefined) newState[projectId] = [];
        newState[projectId].push(newFiles);
        setFiles(newState);
        setLoadingFiles(false);
    }
    const getActiveFiles = (id) => {
        return (files[id] || []).filter((obj) => obj.per_page === perPage).flatMap((obj) => obj.files)
    }

    useEffect(() => {
        if (info !== null && projectId === null) {
            setProjectId(Object.keys(info.status.account_info.drive)[0]);
        }
    }, [info])

    useEffect(() => {
        if (projectId !== null) {
            if (files[projectId] && files[projectId].find((f) => f.page === 0) === undefined) setPage(0);
            fetchFiles();
        }
    }, [projectId, page]);

    useEffect(() => {
        // setFiles(null);
        // setPage(0)
    }, [perPage]);

    const loadNextPage = () => {
        setPage(page + 1);
    }

    return (
        <div className="py-4 px-4 w-100 h-100 d-flex flex-column">
            {loading ? (
                <div className="h-100 w-100 d-flex justify-content-center align-items-center">
                    <Loading/>
                </div>
            ) : (
                <div className="d-flex align-items-start">
                    <Tab.Container activeKey={projectId}>
                        <Nav variant="pills" className="flex-column text-nowrap" style={{position: "sticky", top: "16px"}}>
                            <h5 className="navbar-brand">Project</h5>
                            {
                                Object.keys(info.status.account_info.drive).map((id) => (
                                    <Nav.Item>
                                        <Nav.Link eventKey={id} onClick={() => setProjectId(id)}>{id}</Nav.Link>
                                    </Nav.Item>
                                ))
                            }
                        </Nav>
                        <Tab.Content className="pl-3 flex-grow-1">
                            {
                                Object.keys(info.status.account_info.drive).map((id) => (
                                    <Tab.Pane eventKey={id}>
                                        <div style={{display:"grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gridAutoRows: "auto", gap: "20px", wordBreak: "break-all"}}>
                                            {
                                                getActiveFiles(id).map((file) => (
                                                    <FileCard file={file}/>
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
                <Card.Text>
                    <div>Size: {prettyBytes(parseInt(file.fileSize)).replace(" ", "")}</div>
                    <div>Created: {moment(file.createdDate).fromNow()}</div>
                </Card.Text>
                {cardEmbed()}
            </Card.Body>
        </Card>
    );
}