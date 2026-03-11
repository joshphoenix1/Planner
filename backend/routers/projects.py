from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import subprocess

from database import get_db
import models
import schemas

router = APIRouter(prefix="/projects", tags=["projects"])


def call_claude_cli(prompt: str) -> str:
    """Call Claude CLI"""
    try:
        env = {
            "HOME": "/home/ubuntu",
            "PATH": "/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin",
            "USER": "ubuntu",
        }
        result = subprocess.run(
            ["/home/ubuntu/.local/bin/claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            timeout=120,
            text=True,
            env=env
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return ""


@router.get("/", response_model=List[schemas.ProjectWithStats])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.updated_at.desc()).all()
    result = []
    for p in projects:
        task_count = db.query(models.Task).filter(models.Task.project_id == p.id).count()
        completed_count = db.query(models.Task).filter(
            models.Task.project_id == p.id,
            models.Task.status == "done"
        ).count()
        epic_count = db.query(models.Epic).filter(models.Epic.project_id == p.id).count()
        sprint_count = db.query(models.Sprint).filter(models.Sprint.project_id == p.id).count()

        result.append(schemas.ProjectWithStats(
            **schemas.Project.model_validate(p).model_dump(),
            task_count=task_count,
            completed_count=completed_count,
            epic_count=epic_count,
            sprint_count=sprint_count
        ))
    return result


@router.post("/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/{project_id}", response_model=schemas.ProjectWithStats)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task_count = db.query(models.Task).filter(models.Task.project_id == project_id).count()
    completed_count = db.query(models.Task).filter(
        models.Task.project_id == project_id,
        models.Task.status == "done"
    ).count()
    epic_count = db.query(models.Epic).filter(models.Epic.project_id == project_id).count()
    sprint_count = db.query(models.Sprint).filter(models.Sprint.project_id == project_id).count()

    return schemas.ProjectWithStats(
        **schemas.Project.model_validate(project).model_dump(),
        task_count=task_count,
        completed_count=completed_count,
        epic_count=epic_count,
        sprint_count=sprint_count
    )


@router.put("/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, update: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@router.post("/{project_id}/generate-from-repo")
def generate_from_repo(project_id: int, db: Session = Depends(get_db)):
    """Generate project description from git repo analysis"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo_info = []

    # Try to find local repo path
    project_name = project.name.lower().replace(" ", "-").replace("_", "-")
    possible_paths = []

    # Check github_url for repo name first (most reliable)
    if project.github_url:
        repo_name = project.github_url.rstrip("/").split("/")[-1].replace(".git", "")
        possible_paths.extend([
            f"/home/ubuntu/projects/{repo_name}",
            f"/home/ubuntu/{repo_name}",
            f"/home/ubuntu/repos/{repo_name}",
        ])

    # Then try variations of project name
    possible_paths.extend([
        f"/home/ubuntu/projects/{project_name}",
        f"/home/ubuntu/{project_name}",
        f"/home/ubuntu/repos/{project_name}",
        f"/home/ubuntu/projects/{project.name}",
        f"/home/ubuntu/{project.name}",
    ])

    local_path = None
    for path in possible_paths:
        try:
            result = subprocess.run(["git", "-C", path, "status"], capture_output=True, timeout=5)
            if result.returncode == 0:
                local_path = path
                break
        except:
            pass

    # If no local repo found, try to clone from github
    if not local_path and project.github_url:
        try:
            import os
            github_token = os.environ.get("GITHUB_TOKEN")
            repo_name = project.github_url.rstrip("/").split("/")[-1].replace(".git", "")
            clone_path = f"/home/ubuntu/projects/{repo_name}"
            subprocess.run(["mkdir", "-p", "/home/ubuntu/projects"], capture_output=True)

            # Use token for auth if available
            if github_token and "github.com" in project.github_url:
                auth_url = project.github_url.replace("https://", f"https://{github_token}@")
            else:
                auth_url = project.github_url

            clone_result = subprocess.run(
                ["git", "clone", "--depth", "1", auth_url, clone_path],
                capture_output=True, text=True, timeout=60
            )
            if clone_result.returncode == 0:
                local_path = clone_path
                repo_info.append("(Repo cloned from GitHub)")
        except:
            pass

    if local_path:
        # Analyze local repo
        try:
            # Get README or other docs
            for doc_file in ["README.md", "CLAUDE.md", "README.rst", "README.txt", "DEPLOYMENT_GUIDE.md"]:
                readme_result = subprocess.run(
                    ["cat", f"{local_path}/{doc_file}"],
                    capture_output=True, text=True, timeout=5
                )
                if readme_result.returncode == 0 and readme_result.stdout.strip():
                    repo_info.append(f"{doc_file}:\n{readme_result.stdout[:3000]}")
                    break

            # Get recent commits
            log_result = subprocess.run(
                ["git", "-C", local_path, "log", "--oneline", "-20"],
                capture_output=True, text=True, timeout=5
            )
            if log_result.returncode == 0:
                repo_info.append(f"Recent commits:\n{log_result.stdout}")

            # Get file structure - list all code files
            ls_result = subprocess.run(
                ["ls", "-la", local_path],
                capture_output=True, text=True, timeout=5
            )
            if ls_result.returncode == 0:
                repo_info.append(f"Directory listing:\n{ls_result.stdout}")

            # Get python/js files
            for ext in ["*.py", "*.js", "*.ts"]:
                find_result = subprocess.run(
                    ["find", local_path, "-maxdepth", "2", "-name", ext],
                    capture_output=True, text=True, timeout=10
                )
                if find_result.returncode == 0 and find_result.stdout.strip():
                    files = [f.replace(local_path + "/", "") for f in find_result.stdout.strip().split("\n") if f][:30]
                    if files:
                        repo_info.append(f"Code files ({ext}):\n" + "\n".join(files))

            # Get package.json or requirements.txt
            for dep_file in ["package.json", "requirements.txt", "Cargo.toml", "go.mod", "pyproject.toml"]:
                dep_result = subprocess.run(
                    ["cat", f"{local_path}/{dep_file}"],
                    capture_output=True, text=True, timeout=5
                )
                if dep_result.returncode == 0:
                    repo_info.append(f"{dep_file}:\n{dep_result.stdout[:1500]}")
                    break

        except Exception as e:
            repo_info.append(f"Error analyzing repo: {str(e)}")
    else:
        repo_info.append("No local repository found. Set up the repo path or clone it first.")

    if not repo_info or (len(repo_info) == 1 and "No local" in repo_info[0]):
        return {"message": "Could not find local repository", "description": None}

    repo_text = "\n\n".join(repo_info)

    prompt = f"""PROJECT: {project.name}

INFO:
{repo_text[:3500]}

Write exactly 2 sentences. Sentence 1: what the software does. Sentence 2: tech stack. Maximum 40 words total. No preamble. Start with a verb or noun, never "Based on" or "This is"."""

    description = call_claude_cli(prompt)

    if description:
        # Clean up common preambles
        clean = description.strip()

        # If Claude is asking for permission, generate a fallback description
        if "permission" in clean.lower() or "Could you grant" in clean:
            clean = f"Software project. Check repository for details."

        for prefix in ["Based on", "Here's", "Here is", "This is a", "The project"]:
            if clean.startswith(prefix):
                # Skip the preamble line
                parts = clean.split('\n\n', 1)
                if len(parts) > 1:
                    clean = parts[1].strip()
                else:
                    # Try to find content after colon
                    if ':' in clean[:50]:
                        clean = clean.split(':', 1)[1].strip()

        # Remove markdown formatting
        clean = clean.replace("**", "").replace("*", "").replace("#", "").strip()
        project.description = clean
        db.commit()
        return {"message": "Description generated from repo", "description": clean}
    else:
        return {"message": "Failed to generate description", "description": None}


@router.post("/{project_id}/generate-notes")
def generate_project_notes(project_id: int, db: Session = Depends(get_db)):
    """Generate/refresh project notes from all project emails using AI"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all emails for this project
    emails = db.query(models.Email).filter(
        models.Email.project_id == project_id
    ).order_by(models.Email.received_at.desc()).limit(20).all()

    if not emails:
        return {"message": "No emails found for this project", "notes": None}

    # Build email summary for AI
    email_summaries = []
    for e in emails:
        email_summaries.append(f"""
--- Email ---
Subject: {e.subject}
From: {e.sender}
Date: {e.received_at}
Content: {e.body[:1500] if e.body else e.snippet[:500]}
""")

    emails_text = "\n".join(email_summaries[:10])  # Limit to 10 most recent

    prompt = f"""Analyze these project emails and create a comprehensive project summary.

PROJECT: {project.name}
{project.description or ''}

EMAILS:
{emails_text}

Create a project summary that includes:
1. **Project Overview** - What is this project about? (2-3 sentences)
2. **Key Contacts** - Who are the main stakeholders/contacts?
3. **Current Status** - What's the current state based on recent emails?
4. **Action Items** - What needs to be done?
5. **Important Dates** - Any deadlines or milestones mentioned?
6. **Notes** - Any other important information

Write in markdown format. Be concise but comprehensive."""

    notes = call_claude_cli(prompt)

    if notes:
        project.notes = notes
        db.commit()
        return {"message": "Notes generated successfully", "notes": notes}
    else:
        return {"message": "Failed to generate notes", "notes": None}
