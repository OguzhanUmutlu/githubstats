import os
import time
from collections import defaultdict
from pathlib import Path
from subprocess import DEVNULL, call

import requests

CODE_LANGUAGES = {
    ".py": "Python", ".cpp": "C++", ".c": "C", ".h": "C/C++ Header", ".hpp": "C++ Header",
    ".js": "JavaScript", ".html": "HTML", ".css": "CSS", ".java": "Java", ".go": "Go",
    ".php": "PHP", ".rs": "Rust", ".ts": "TypeScript", ".jsx": "JavaScript (React)", ".tsx": "TypeScript (React)",
    ".cmd": "Batch", ".bat": "Batch", ".mjs": "JavaScript (ES Modules)",
    ".mts": "TypeScript (ES Modules)", ".rjs": "JavaScript (React Native)"}


def get_repos(github_user, token):
    repos = []

    params = {
        "per_page": 100,
        "page": 1
    }

    headers = {"Authorization": f"token {token}"} if token else dict()

    while True:
        if token:
            url = f"https://api.github.com/user/repos"
        else:
            url = f"https://api.github.com/users/{github_user}/repos"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200 or not response.json():
            break

        rs = response.json()

        for r in rs:
            if r["fork"]:
                print(f"Skipping forked repository: {r['full_name']}")
            else:
                repos.append(r)

        params["page"] += 1

    print(len(repos), "repositories were found!")
    return [repo["clone_url"] for repo in repos]


def clone_repo(repo_url, clone_dir, token, repo_num, repo_count):
    repo_name = repo_url.split("/")[-1][:-4]
    repo_path = clone_dir / repo_name

    if repo_path.exists():
        print(f"{repo_num}/{repo_count}   Pulling {repo_name}...")
        call("cd " + str(repo_path) + " && git pull", shell=True, stdout=DEVNULL, stderr=DEVNULL)
    else:
        print(f"{repo_num}/{repo_count}   Cloning {repo_name}...")

        if token:
            git_clone_cmd = f"git clone https://{token}:x-oauth-basic@{repo_url.split("https://")[1]} {repo_path}"
        else:
            git_clone_cmd = f"git clone {repo_url} {repo_path}"

        call(git_clone_cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL)

    return repo_path


def get_file_stats(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            # (lines, characters)
            r = f.read()
            return sum(1 for line in r.splitlines() if line.strip()), sum(1 for char in r if not char.isspace())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0, 0


def get_repo_stats(repo_path, ignored_extensions):
    repo_lines = defaultdict(int)
    total_lines = 0
    total_chars = 0
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            file_extension = Path(file).suffix
            if file_extension in CODE_LANGUAGES:
                file_path = Path(root) / file
                lines, chars = get_file_stats(file_path)
                language = CODE_LANGUAGES[file_extension]

                repo_lines[language] += lines
                total_lines += lines
                total_chars += chars
            else:
                ignored_extensions.add(file_extension)
    return repo_lines, total_lines, total_chars


def main(github_user, token):
    total_lines_of_code = 0
    total_chars_of_code = 0
    language_stats = defaultdict(int)
    repo_stats = {}
    clone_dir = Path("./repos")
    out_dir = Path("./out")
    repo_num = 0
    ignored_extensions = set()

    start_time = time.time()

    if not clone_dir.exists():
        clone_dir.mkdir()

    if not out_dir.exists():
        out_dir.mkdir()

    repos = get_repos(github_user, token)
    repo_count = len(repos)

    for repo_url in repos:
        repo_num += 1
        repo_name = repo_url.split("/")[-1][:-4]
        repo_path = clone_repo(repo_url, clone_dir, token, repo_num, repo_count)
        repo_lines_by_lang, repo_total_lines, repo_total_chars = get_repo_stats(repo_path,
                                                                                ignored_extensions)
        repo_stats[repo_name] = repo_total_lines, repo_total_chars

        for lang, lines in repo_lines_by_lang.items():
            language_stats[lang] += lines

        total_lines_of_code += repo_total_lines
        total_chars_of_code += repo_total_chars

    line_sorted_repos = sorted(repo_stats.items(), key=lambda x: x[1][0], reverse=True)
    print("\nTop 5 repositories by lines of code:")
    for repo, stats in line_sorted_repos[:5]:
        print(f"{repo}: {stats[0]} lines of code")

    char_sorted_repos = sorted(repo_stats.items(), key=lambda x: x[1][1], reverse=True)
    print("\nTop 5 repositories by characters of code:")
    for repo, stats in char_sorted_repos[:5]:
        print(f"{repo}: {stats[1]} characters of code")

    sorted_languages = sorted(language_stats.items(), key=lambda x: x[1], reverse=True)
    print("\nTop 5 languages by total lines of code:")
    for lang, lines in sorted_languages[:5]:
        print(f"{lang}: {lines} lines of code")

    with open(out_dir / "repos-lines.txt", "w") as repo_file:
        for repo, stats in line_sorted_repos:
            repo_file.write(f"{repo}: {stats[0]} lines of code\n")

    with open(out_dir / "repos-chars.txt", "w") as repo_file:
        for repo, stats in line_sorted_repos:
            repo_file.write(f"{repo}: {stats[1]} chars of code\n")

    with open(out_dir / "languages.txt", "w") as lang_file:
        for lang, lines in sorted_languages:
            lang_file.write(f"{lang}: {lines} lines of code\n")

    ignored_extensions.discard("")
    ignored_extensions_list = ", ".join(sorted(ignored_extensions))
    print(f"\nIgnored file extensions: {ignored_extensions_list}")

    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nTime taken: {total_time:.2f} seconds")

    print(f"\nTotal lines of code for {github_user}: {total_lines_of_code}")
    print(f"\nTotal characters of code for {github_user}: {total_chars_of_code}")
    print(f"Total repositories counted: {repo_num}")


if __name__ == "__main__":
    github_user = input("Enter the GitHub username: ")
    try:
        with open("token.txt", "r") as f:
            main(github_user, f.read().strip())
    except FileNotFoundError:
        print("Continuing without token. Set token.txt with your github token in it to include private repositories.")
        main(github_user, "")
