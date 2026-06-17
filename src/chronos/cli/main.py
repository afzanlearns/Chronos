import sys
from pathlib import Path
from datetime import datetime, timedelta
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from chronos.db import get_session, init_db, ensure_default_user
from chronos.analytics.analytics import AnalyticsEngine
from chronos.tasks.task_manager import TaskManager
from chronos.notifications.notifier import NotificationService
from chronos.config import settings

console = Console()


@click.group()
def cli():
    """Chronos — Track app usage and tasks"""
    pass


@cli.command()
def setup():
    """Initialize Chronos database and configuration"""
    with console.status("[bold green]Setting up Chronos..."):
        engine = init_db()
        session = get_session(engine)
        ensure_default_user(session)
        session.close()

    config_dir = Path.home() / ".chronos"
    config_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel.fit(
        "[bold green]Chronos is ready![/bold green]\n\n"
        f"Database: [cyan]{config_dir / 'chronos.db'}[/cyan]\n"
        f"Config: [cyan]{config_dir / 'config.yml'}[/cyan]\n\n"
        "Run [bold]chronos --help[/bold] to see available commands.",
        title="Setup Complete"
    ))


@cli.group()
def report():
    """Generate productivity reports"""
    pass


@report.command()
@click.option('--date', type=str, default='today', help='Date: today, week, or YYYY-MM-DD')
def daily(date):
    """Show daily productivity report"""
    session = get_session()
    user = ensure_default_user(session)
    analytics = AnalyticsEngine(session)

    if date == 'today':
        report_date = datetime.now().date()
    elif date == 'week':
        report_date = (datetime.now() - timedelta(days=7)).date()
    else:
        try:
            report_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD or 'today'[/red]")
            return

    stats = analytics.get_daily_stats(user.id, report_date)
    breakdown = analytics.get_app_breakdown(user.id, report_date)

    console.print(Panel.fit(
        f"[bold]Date:[/bold] {report_date}\n"
        f"[bold]Screen Time:[/bold] {int((stats.total_screen_time_seconds or 0) / 60)}m\n"
        f"[bold]Focus Time:[/bold] {int((stats.focus_time_seconds or 0) / 60)}m\n"
        f"[bold]Tasks Completed:[/bold] {stats.tasks_completed or 0}\n"
        f"[bold]Productivity Score:[/bold] {stats.productivity_score or 0}/100",
        title="Daily Report"
    ))

    if breakdown:
        table = Table(title="App Breakdown")
        table.add_column("App", style="cyan")
        table.add_column("Time", style="magenta")
        table.add_column("Sessions", style="green")

        for b in breakdown:
            table.add_row(
                b['app'] or 'Unknown',
                f"{int(b['time_minutes'])}m",
                str(b['sessions'])
            )
        console.print(table)

    session.close()


@report.command()
def weekly():
    """Show weekly productivity report"""
    session = get_session()
    user = ensure_default_user(session)
    analytics = AnalyticsEngine(session)
    report_data = analytics.get_weekly_report(user.id)

    st = int(report_data['total_screen_time'] / 60)
    ft = int(report_data['focus_time'] / 60)
    tc = report_data['tasks_completed']
    sc = report_data['avg_daily_score']
    bd = report_data['best_day'] or 'N/A'
    wd = report_data['worst_day'] or 'N/A'

    content = (
        f"[bold]Total Screen Time:[/bold] {st}m\n"
        f"[bold]Focus Time:[/bold] {ft}m\n"
        f"[bold]Tasks Completed:[/bold] {tc}\n"
        f"[bold]Avg Daily Score:[/bold] {sc:.1f}/100\n"
        f"[bold]Best Day:[/bold] {bd}\n"
        f"[bold]Worst Day:[/bold] {wd}"
    )
    console.print(Panel(content, title="Weekly Report"))
    session.close()


@cli.group()
def task():
    """Manage tasks"""
    pass


@task.command()
@click.argument('title')
@click.option('--due', type=str, help='Due date (YYYY-MM-DD)')
@click.option('--estimate', type=str, help='Estimated duration (e.g., 2h, 30m)')
@click.option('--priority', type=click.Choice(['low', 'medium', 'high']), default='medium')
def add(title, due, estimate, priority):
    """Add a new task"""
    session = get_session()
    user = ensure_default_user(session)
    manager = TaskManager(session, NotificationService)

    due_date = None
    if due:
        due_date = datetime.strptime(due, '%Y-%m-%d')

    estimated_minutes = None
    if estimate:
        if estimate.endswith('h'):
            estimated_minutes = int(estimate[:-1]) * 60
        elif estimate.endswith('m'):
            estimated_minutes = int(estimate[:-1])
        else:
            estimated_minutes = int(estimate)

    manager.add_task(
        user_id=user.id,
        title=title,
        due_date=due_date,
        estimated_minutes=estimated_minutes,
        priority=priority
    )
    console.print(f"[green]Task added:[/green] {title}")
    session.close()


@task.command()
@click.argument('task_id', type=int)
def complete(task_id):
    """Mark a task as complete"""
    session = get_session()
    manager = TaskManager(session, NotificationService)
    task = manager.complete_task(task_id)
    if task:
        console.print(f"[green]Task completed:[/green] {task.title}")
    else:
        console.print("[red]Task not found[/red]")
    session.close()


@task.command()
def list():
    """List all tasks"""
    session = get_session()
    user = ensure_default_user(session)
    tasks = TaskManager(session, NotificationService).get_all_tasks(user.id)

    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        return

    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Priority", style="magenta")
    table.add_column("Due", style="yellow")

    for t in tasks:
        table.add_row(
            str(t.id),
            t.title,
            t.status,
            t.priority,
            t.due_date.strftime('%Y-%m-%d') if t.due_date else '-'
        )
    console.print(table)
    session.close()


@cli.group()
def limit():
    """Manage app time limits"""
    pass


@limit.command()
@click.argument('app_name')
@click.argument('minutes', type=int)
def set(app_name, minutes):
    """Set daily limit for an app (in minutes)"""
    session = get_session()
    user = ensure_default_user(session)
    from chronos.models.models import ProductivityGoal

    goal = ProductivityGoal(
        user_id=user.id,
        app_name=app_name,
        daily_limit_minutes=minutes
    )
    session.add(goal)
    session.commit()
    console.print(f"[green]Limit set:[/green] {app_name} — {minutes} min/day")
    session.close()


@cli.group()
def focus():
    """Manage focus sessions"""
    pass


@focus.command()
@click.option('--duration', type=int, default=90, help='Duration in minutes')
@click.option('--task', type=str, default=None, help='Focus task description')
@click.option('--block', type=str, default=None, help='Comma-separated apps to block')
def start(duration, task, block):
    """Start a focus session"""
    session = get_session()
    from chronos.models.models import FocusSession
    from datetime import datetime

    focus_session = FocusSession(
        start_time=datetime.now(),
        duration_minutes=duration,
        focus_task=task,
        blocked_apps=block,
        interruptions_count=0
    )
    session.add(focus_session)
    session.commit()

    console.print(Panel.fit(
        f"[bold]Focus session started![/bold]\n"
        f"Duration: {duration} min\n"
        f"Task: {task or 'Not specified'}\n"
        f"Blocked: {block or 'None'}",
        title="Focus Mode"
    ))
    session.close()


@cli.command()
def streaks():
    """View productivity streaks"""
    session = get_session()
    user = ensure_default_user(session)
    analytics = AnalyticsEngine(session)

    from chronos.models.models import DailyStat
    stats = session.query(DailyStat).filter_by(user_id=user.id)\
        .order_by(DailyStat.date.desc()).limit(30).all()

    if not stats:
        console.print("[yellow]No data yet. Start tracking to see streaks![/yellow]")
        session.close()
        return

    current_streak = 0
    best_streak = 0
    streak_count = 0

    for s in sorted(stats, key=lambda x: x.date):
        if s.productivity_score and s.productivity_score >= 60:
            streak_count += 1
            current_streak = streak_count
            best_streak = max(best_streak, streak_count)
        else:
            streak_count = 0

    console.print(Panel.fit(
        f"[bold]Current Streak:[/bold] {current_streak} days\n"
        f"[bold]Best Streak:[/bold] {best_streak} days\n"
        f"[bold]Days Tracked:[/bold] {len(stats)}",
        title="Productivity Streaks"
    ))
    session.close()


@cli.command()
@click.option('--analyze', is_flag=True, help='Analyze interruption patterns')
def interruptions(analyze):
    """View and analyze interruptions"""
    session = get_session()
    user = ensure_default_user(session)

    from chronos.models.models import FocusSession
    focus_sessions = session.query(FocusSession).filter(
        FocusSession.interruptions_count > 0
    ).order_by(FocusSession.start_time.desc()).limit(20).all()

    if not focus_sessions:
        if analyze:
            console.print("[yellow]No interruptions recorded yet.[/yellow]")
        else:
            console.print("[yellow]No interruptions data available.[/yellow]")
        session.close()
        return

    table = Table(title="Recent Interruptions")
    table.add_column("Date", style="cyan")
    table.add_column("Task", style="white")
    table.add_column("Interruptions", style="red")
    table.add_column("Duration", style="green")

    for fs in focus_sessions:
        table.add_row(
            fs.start_time.strftime('%Y-%m-%d %H:%M'),
            fs.focus_task or '-',
            str(fs.interruptions_count),
            f"{fs.duration_minutes}m" if fs.duration_minutes else '-'
        )
    console.print(table)
    session.close()


@cli.command()
@click.option('--port', type=int, default=None, help='Port for the API server')
def serve(port):
    """Start the Chronos API server"""
    if port is None:
        port = settings.FLASK_PORT

    from chronos.api.routes import create_app
    app = create_app()

    console.print(f"[green]Chronos API server starting on port {port}...[/green]")
    app.run(host='0.0.0.0', port=port, debug=settings.FLASK_DEBUG)


if __name__ == '__main__':
    cli()
