import React, { Component, useState, useMemo, useEffect } from 'react';
import { Card, Button, Tab, Nav } from 'react-bootstrap';
import { FaFileArchive, FaFile } from 'react-icons/fa';
import moment from 'moment';
import prettyBytes from 'pretty-bytes';
import useAbortController from './hooks/use-abort-controller';
import Api from './Api';
import Loading from './Loading';
import { delay } from './common';

export default function DriveInfo({ info, searchQuery }) {
    const [projectId, setProjectId] = useState(null);
    const loading = projectId === null;
    useEffect(() => {
        if (projectId === null && info !== null) setProjectId(Object.keys(info.status.account_info.drive)[0]);
    }, [info]);

    return (
        <div className="py-4 px-4 w-100">
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
                                        <DriveFiles projectId={id} searchQuery={searchQuery}/>
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
/*
function DriveFiles({ projectId, searchQuery }) {
    const [page, setPage] = useState(0);
    const [perPage, setPerPage] = useState(2);
    const [loadingFiles, setLoadingFiles] = useState(false);
    const [files, setFiles] = useState([]);
    const getSignal = useAbortController();

    const activeFiles = useMemo(() => {
        return files.reduce((acc, cur) => {
            const searchTerm = (searchQuery === "" || searchQuery === undefined) ? null : searchQuery;
            const dupe = acc.filter((obj) => obj.page === cur.page && obj.per_page === cur.per_page && obj.search_term === cur.search_term).length > 0;
            if (
                cur.per_page === perPage &&
                cur.search_term === searchTerm &&
                !dupe
            ) acc.push(cur);
            return acc;
        }, []);
    }, [perPage, files, searchQuery]);
    const flatActiveFiles = useMemo(() => activeFiles.flatMap((obj) => obj.files), [activeFiles]);
    const [loadedResults, totalResults, lastPageLoaded] = useMemo(() => {
        return [
            flatActiveFiles.length,
            activeFiles.length === 0 ? 0 : activeFiles[0].total,
            activeFiles.some((obj) => obj.page + 1 === obj.pages)
        ]
    }, [activeFiles]);

    useEffect(async () => {
        const signal = getSignal();
        setLoadingFiles(true);
        const searchTerm = (searchQuery === "" || searchQuery === undefined) ? null : searchQuery;
        if (files.find((obj) => obj.page === page && obj.per_page === perPage && obj.search_term === searchTerm) === undefined) {
            try {
                const newFiles = await Api.getDriveFiles(projectId, page, perPage, searchQuery, { signal });
                setFiles([
                    ...files,
                    newFiles
                ]);
            } catch (e) {
                if (e.name !== "AbortError") throw e;
            }
        } else {
            console.log(`Already have search results for page=${page}, per_page=${perPage}, and search_term=${searchQuery}`);
        }
        console.log("set loading false");
        setLoadingFiles(false);
    }, [page, searchQuery]);

    useEffect(() => {
        setPage(activeFiles.length === 0 ? 0 : activeFiles.sort((a, b) => b.page - a.page)[0].page);
    }, [searchQuery]);

    const loadNextPage = () => {
        setPage(page + 1);
    }
    return (
        <div className="drive-files h-100">
            {
                flatActiveFiles.length === 0 ? (
                    <div className="d-flex justify-content-center align-items-center h-100">
                        <Loading/>
                    </div>
                ) : (
                    <>
                    {!loadingFiles && (<>
                        <h5 className="mb-3">Showing {loadedResults} of {totalResults} results</h5>
                    </>)}
                    <div style={{
                        display:"grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                        gridAutoRows: "auto",
                        gap: "20px",
                        wordBreak: "break-all"
                    }}>
                        {
                            flatActiveFiles.map((file) => (
                                <FileCard file={file} key={file.id}/>
                            ))
                        }
                    </div>
                    <div className="d-flex justify-content-center mt-3">
                        {
                            loadingFiles ? (
                                <Loading/>
                            ) : (
                                !lastPageLoaded && <Button variant="outline-primary" onClick={loadNextPage}>Load more</Button>
                            )
                        }
                    </div>
                    </>
                )
            }
            
        </div>
    );
}
*/

class DriveFiles extends Component {
    constructor(props) {
        super(props);

        this.state = {
            files: [],
            perPage: 50,
            fetchingFiles: []
        };
    }
    getSearchTerm() {
        return (this.props.searchQuery === "" || this.props.searchQuery === undefined) ? null : this.props.searchQuery;
    }
    getNextPage() {
        const activeFiles = this.getActiveFiles();
        // If there are no pages loaded, page 0 is the next page.
        // Otherwise, get the obj with the highest page number, and return 1 greater
        return activeFiles.length === 0 ? 0 : activeFiles.sort((a, b) => b.page - a.page)[0].page + 1;
    }
    getFilePage(files, page, perPage, searchTerm) {
        return files.find((obj) => obj.page === page && obj.per_page === perPage && obj.search_term === searchTerm);
    }
    async getFiles(page) {
        
        const { fetchingFiles } = this.state;
        const args = [page, this.state.perPage, this.getSearchTerm()]
        if (this.getFilePage(fetchingFiles, ...args) !== undefined || this.getFilePage(this.state.files, ...args) !== undefined) {
            return;
        }
        fetchingFiles.push({
            page,
            per_page: this.state.perPage,
            search_term: this.getSearchTerm()
        })
        this.setState({ fetchingFiles });
        const newFiles = await Api.getDriveFiles(this.props.projectId, page, this.state.perPage, this.props.searchQuery);
        const { files } = this.state;
        
        // Only add if it isn't a dupe (two requests for same page fired).
        if (this.getFilePage(files, newFiles.page, newFiles.per_page, newFiles.search_term) === undefined) files.push(newFiles);

        this.setState({ files, fetchingFiles: this.state.fetchingFiles.filter((p) => p !== this.getFilePage(this.state.fetchingFiles, ...args)) });
    }
    getActiveFiles() {
        return this.state.files.reduce((acc, cur) => {
            const searchTerm = this.getSearchTerm();
            const dupe = acc.filter(
                (obj) => obj.page === cur.page && obj.per_page === cur.per_page && obj.search_term === cur.search_term
            ).length > 0;
            if (
                cur.per_page === this.state.perPage &&
                cur.search_term === searchTerm &&
                !dupe
            ) acc.push(cur);
            return acc;
        }, []);
    }
    isPageLoading(page) {
        const { fetchingFiles } = this.state;
        return this.getFilePage(fetchingFiles, page, this.state.perPage, this.getSearchTerm()) !== undefined;
    }
    nextPageLoading() {
        return this.isPageLoading(this.getNextPage());
    }
    loadNextPage() {
        this.getFiles(this.getNextPage());
    }
    componentDidUpdate(prevProps) {
        if (this.props.searchQuery !== prevProps.searchQuery) {
            this.getFiles(0);
        }
    }
    componentDidMount() {
        this.getFiles(0);
    }
    render() {
        const activeFiles = this.getActiveFiles();
        const flatActiveFiles = activeFiles.flatMap((obj) => obj.files);
        const totalResults = activeFiles.length === 0 ? 0 : activeFiles[0].total;
        const loadedResults = flatActiveFiles.length;
        const lastPageLoaded = loadedResults === totalResults;
        return (
            <div className="drive-files h-100 d-flex flex-column">
                {
                    this.isPageLoading(0) ? (
                        <div className="d-flex justify-content-center align-items-center h-100">
                            <Loading/>
                        </div>
                    ) : (
                        <>
                        {this.getSearchTerm() !== null ? (
                            <>
                            <h5>Search results for: {this.props.searchQuery}</h5>
                            <h6 className="mb-3 text-muted">Showing {loadedResults} of {totalResults} results</h6>
                            </>
                        ) : (
                            <h5 className="mb-3">Showing {loadedResults} of {totalResults} results</h5>
                        )}
                        <div style={{
                            display:"grid",
                            gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                            gridAutoRows: "auto",
                            gap: "20px",
                            wordBreak: "break-all"
                        }}>
                            {
                                flatActiveFiles.map((file) => (
                                    <FileCard file={file} key={file.id}/>
                                ))
                            }
                        </div>
                        <div className="d-flex justify-content-center mt-3 flex-grow-1 align-items-end">
                            {
                                this.nextPageLoading() ? (
                                    <Loading/>
                                ) : (
                                    !lastPageLoaded && <Button variant="outline-primary" onClick={() => this.loadNextPage()}>Load more</Button>
                                )
                            }
                        </div>
                        </>
                    )
                }
                
            </div>
        );
    }
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