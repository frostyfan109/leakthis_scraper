import sys
import os
from db import *


if __name__ == "__main__":
    session = session_factory()

    args = sys.argv[1:]
    if args[0] == "get":
        if args[1] == "recent":
            if args[2] == "leaks":
                pass
            elif args[2] == "entries":
                if len(args) == 4:
                    count = int(args[3])
                else:
                    count = 5
                posts = session.query(Post).order_by(Post.id.desc()).limit(count)[::-1]
                for post in posts:
                    print(post)
                    for file in post.get_files():
                        print("--> " + str(file))
                    print()

    session.close()
