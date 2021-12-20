import url_parser

def test_parse_onlyfiles_biz():
    url = "https://onlyfiles.biz/file.php?id=frglrn2gkg1gtsc&type=mp3"
    parser = url_parser.URLParser()

    assert parser.parse_download_url(url) == "https://www.onlyfiles.biz/files/frglrn2gkg1gtsc.mp3"

    hosting_service = parser.get_hosting_service(url)
    assert isinstance(hosting_service, url_parser.OnlyFilesBiz)
    assert hosting_service.parse_file_name(url) == "Wake_The_Dead_Pierre_Beat.mp3"

    assert parser.download("https://onlyfiles.biz/file.php?id=&type=mp3")["unknown"] == True

def test_parse_dbree():
    url = "https://dbree.org/v/d12739"
    parser = url_parser.URLParser()

    # Can't test parsing the download url because it isn't static and it's unclear how the url is generated.
    # NOTE: When requests mocking is added, this can be tested because the download url will be static.
    # assert parser.parse_download_url(url) == "https://dbree.org/d/d12739/988b9043272dcb2955ac06e4d3d7f1d7"

    hosting_service = parser.get_hosting_service(url)
    assert isinstance(hosting_service, url_parser.DBREE)
    assert hosting_service.parse_file_name(url) == "juice spanglish master01.mp3"

    # Make sure that it correctly throws for nonexistent urls
    # For now use a url that is guarenteed not to exist to test this.
    # When requests mocking is added, this can be changed.
    assert parser.download("https://dbree.org/v/")["unknown"] == True

def test_parse_anonfiles():
    url = "https://anonfiles.com/heve4700p2"
    parser = url_parser.URLParser()

    hosting_service = parser.get_hosting_service(url)
    assert isinstance(hosting_service, url_parser.AnonFiles)
    assert hosting_service.parse_file_name(url) == "Juice WRLD A .mp3"

    assert parser.download("https://anonfiles.com/%20")["unknown"] == True
