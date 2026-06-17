import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import BarColumn, Progress
from rich.text import Text

console = Console(safe_box=True, no_color=True)

from chronos.db import get_session, init_db, ensure_default_user
from chronos.analytics.analytics import AnalyticsEngine, format_duration
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
@click.option('--recompute', is_flag=True, default=False, help='Force recompute stats from live data')
def daily(date, recompute):
    """Show daily productivity report with website breakdown"""
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

    stats = analytics.get_daily_stats(user.id, report_date, force=recompute)
    breakdown = analytics.get_app_breakdown(user.id, report_date)
    browser_report = analytics.get_daily_report_with_browser_data(user.id, report_date)

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

    bb = browser_report.get('browser_breakdown', [])
    if bb:
        total_browser = browser_report.get('total_browser_time_formatted', '0m')
        console.print(Panel.fit(
            f"[bold]Total Browser Time:[/bold] {total_browser}",
            title="Website Breakdown"
        ))

        bb_table = Table()
        bb_table.add_column("Domain", style="cyan")
        bb_table.add_column("Time", style="magenta")
        bb_table.add_column("Percentage", style="yellow")
        bb_table.add_column("Visits", style="green")

        for site in bb[:10]:
            bb_table.add_row(
                site['domain'],
                site['duration_formatted'],
                f"({site['percentage']}%)",
                f"[{site['visits']} visits]"
            )
        console.print(bb_table)

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


@report.command()
def monthly():
    """Show monthly productivity report"""
    session = get_session()
    user = ensure_default_user(session)
    analytics = AnalyticsEngine(session)
    report_data = analytics.get_monthly_report(user.id)

    st = int(report_data['total_screen_time'] / 60) if report_data['total_screen_time'] else 0
    ft = int(report_data['focus_time'] / 60) if report_data['focus_time'] else 0
    tc = report_data['tasks_completed']
    sc = report_data['avg_daily_score']
    dt = report_data['days_tracked']
    bd = report_data['best_day'] or 'N/A'
    wd = report_data['worst_day'] or 'N/A'

    content = (
        f"[bold]Total Screen Time:[/bold] {st}m\n"
        f"[bold]Focus Time:[/bold] {ft}m\n"
        f"[bold]Tasks Completed:[/bold] {tc}\n"
        f"[bold]Days Tracked:[/bold] {dt}\n"
        f"[bold]Avg Daily Score:[/bold] {sc:.1f}/100\n"
        f"[bold]Best Day:[/bold] {bd}\n"
        f"[bold]Worst Day:[/bold] {wd}"
    )
    console.print(Panel(content, title="Monthly Report"))
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


@task.command('list')
def list_tasks():
    """List all tasks"""
    session = get_session()
    user = ensure_default_user(session)
    tasks = TaskManager(session, NotificationService).get_all_tasks(user.id)

    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        session.close()
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


@limit.command('set')
@click.argument('app_name')
@click.argument('minutes', type=int)
def set_limit(app_name, minutes):
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
@click.option('--duration', type=int, default=25, help='Duration in minutes')
@click.option('--task', type=str, default=None, help='Focus task description')
@click.option('--block', type=str, multiple=True, help='Apps or websites to block (can use multiple times)')
def start(duration, task, block):
    """Start a focus session"""
    session = get_session()
    from chronos.models.models import FocusSession

    blocked_apps = []
    blocked_urls = []

    for item in block:
        item = item.strip().lower()
        if '.' in item or item in ('youtube', 'reddit', 'twitter', 'facebook', 'instagram',
                                    'tiktok', 'netflix', 'twitch', 'spotify', 'discord'):
            blocked_urls.append(f"{item}.com" if '.' not in item else item)
        else:
            blocked_apps.append(item)

    blocked_apps_str = ','.join(blocked_apps) if blocked_apps else ''
    blocked_urls_str = ','.join(blocked_urls) if blocked_urls else ''

    focus_session = FocusSession(
        start_time=datetime.now(),
        duration_minutes=duration,
        focus_task=task,
        blocked_apps=blocked_apps_str,
        blocked_urls=blocked_urls_str,
        status='active'
    )
    session.add(focus_session)
    session.commit()

    chronos_dir = Path.home() / ".chronos"
    chronos_dir.mkdir(parents=True, exist_ok=True)
    current_focus = {
        'session_id': focus_session.id,
        'start_time': focus_session.start_time.isoformat(),
        'duration_minutes': duration,
        'task': task or '',
        'blocked_apps': blocked_apps,
        'blocked_urls': blocked_urls
    }
    with open(chronos_dir / "current_focus.json", 'w') as f:
        json.dump(current_focus, f, indent=2)

    block_display = []
    if blocked_apps:
        block_display.append(f"Apps: {', '.join(blocked_apps)}")
    if blocked_urls:
        block_display.append(f"Websites: {', '.join(blocked_urls)}")

    content = (
        f"[bold]Task:[/bold] {task or 'Not specified'}\n"
        f"[bold]Duration:[/bold] {duration} min\n"
        f"[bold]Session ID:[/bold] {focus_session.id}\n"
    )
    if block_display:
        content += f"[bold]Blocking:[/bold] {' | '.join(block_display)}\n"
    content += f"\n[yellow]Tip:[/yellow] Use [bold]chronos focus stop[/bold] to end this session"

    console.print(Panel.fit(
        content,
        title="Focus Mode Active"
    ))
    session.close()


@focus.command('stop')
@click.option('--session-id', type=int, default=None, help='Focus session ID (default: auto-detect)')
def stop_focus(session_id):
    """Stop a focus session and show analytics"""
    chronos_dir = Path.home() / ".chronos"
    current_focus_path = chronos_dir / "current_focus.json"

    if session_id is None:
        if current_focus_path.exists():
            with open(current_focus_path) as f:
                data = json.load(f)
            session_id = data.get('session_id')
        else:
            console.print("[red]No active focus session found. Use --session-id to specify one.[/red]")
            return

    session = get_session()
    from chronos.models.models import FocusSession, BrowserActivity, AppSession

    focus_session = session.query(FocusSession).filter_by(id=session_id).first()
    if not focus_session:
        console.print(f"[red]Focus session {session_id} not found.[/red]")
        session.close()
        return

    if focus_session.status == 'completed':
        console.print("[yellow]This session has already ended.[/yellow]")
        session.close()
        return

    now = datetime.now()
    focus_session.end_time = now
    focus_session.status = 'completed'

    actual_duration_seconds = int((now - focus_session.start_time).total_seconds())
    focus_session.actual_duration = actual_duration_seconds

    planned_minutes = focus_session.duration_minutes or 1

    interruptions = 0
    seen_apps = []
    if focus_session.start_time:
        app_sessions = session.query(AppSession).filter(
            AppSession.start_time >= focus_session.start_time,
            AppSession.start_time <= now
        ).all()

        seen_app_ids = set()
        for aps in app_sessions:
            if aps.app_id and aps.app_id not in seen_app_ids:
                seen_app_ids.add(aps.app_id)
                if aps.app and aps.app.display_name:
                    seen_apps.append(aps.app.display_name)

        interruptions = max(0, len(seen_apps) - 1)
        focus_session.interruptions_count = interruptions
        focus_session.app_switches = seen_apps

    blocked_urls_list = []
    if focus_session.blocked_urls:
        blocked_urls_list = [u.strip() for u in focus_session.blocked_urls.split(',') if u.strip()]

    distractions = 0
    urls_hit = []
    if blocked_urls_list:
        browser_activities = session.query(BrowserActivity).filter(
            BrowserActivity.focus_session_id == session_id
        ).all()
        blocked_set = set()
        for ba in browser_activities:
            for blocked in blocked_urls_list:
                if blocked in ba.domain:
                    blocked_set.add(ba.domain)
        distractions = len(blocked_set)
        urls_hit = list(blocked_set)

    focus_session.distractions_caught = distractions

    actual_minutes = actual_duration_seconds / 60
    time_ratio = min(1.0, actual_minutes / planned_minutes) if planned_minutes > 0 else 1
    base_score = int(time_ratio * 100)
    # Ensure minimum base of 50 if no distractions or interruptions
    if interruptions == 0 and distractions == 0:
        base_score = max(base_score, 50)
    score = max(0, min(100, base_score - (interruptions * 5) - (distractions * 3)))
    focus_session.focus_score = score

    session.commit()

    browser_data = session.query(BrowserActivity).filter(
        BrowserActivity.focus_session_id == session_id
    ).all()

    domain_stats = {}
    for bd in browser_data:
        if bd.domain not in domain_stats:
            domain_stats[bd.domain] = {'duration': 0, 'visits': 0}
        domain_stats[bd.domain]['duration'] += bd.duration or 0
        domain_stats[bd.domain]['visits'] += 1

    browser_activity = []
    for domain, stats in sorted(domain_stats.items(), key=lambda x: x[1]['duration'], reverse=True):
        d = stats['duration']
        browser_activity.append({
            'domain': domain,
            'duration_seconds': d,
            'duration_formatted': format_duration(d),
            'visits': stats['visits']
        })

    if current_focus_path.exists():
        current_focus_path.unlink()

    actual_fmt = format_duration(actual_duration_seconds)

    console.print(f"\n[green]v[/green] Focus Session Ended")
    console.print("-" * 52)

    console.print(Panel.fit(
        f"[bold]Task:[/bold] {focus_session.focus_task or 'Not specified'}\n"
        f"[bold]Planned Duration:[/bold] {planned_minutes} min\n"
        f"[bold]Actual Duration:[/bold] {actual_fmt}",
        title="Session Summary"
    ))

    bar_len = 10
    filled = int(score / 100 * bar_len)
    bar = "#" * filled + "-" * (bar_len - filled)
    score_color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    console.print(Panel.fit(
        f"[bold {score_color}]{score}/100[/bold {score_color}] [{bar}]",
        title="Focus Score"
    ))

    if interruptions == 0:
        console.print(Panel.fit("[green]Perfect Focus! No interruptions[/green]", title="Interruptions"))
    else:
        apps_str = ", ".join(seen_apps) if seen_apps else "Unknown apps"
        console.print(Panel.fit(
            f"[yellow]Interruptions:[/yellow] {interruptions}\n"
            f"[dim]Apps: {apps_str}[/dim]",
            title="Interruptions"
        ))

    if distractions > 0:
        urls_str = ", ".join(urls_hit)
        console.print(Panel.fit(
            f"[red]Blocked attempts:[/red] {distractions}\n"
            f"[dim]URLs: {urls_str}[/dim]",
            title="Distractions Blocked"
        ))
    else:
        console.print(Panel.fit("[green]No distractions blocked[/green]", title="Distractions Blocked"))

    if browser_activity:
        ba_table = Table(title="Browser Activity During Focus")
        ba_table.add_column("Domain", style="cyan")
        ba_table.add_column("Time", style="magenta")
        ba_table.add_column("Visits", style="green")
        for ba in browser_activity:
            ba_table.add_row(
                ba['domain'],
                ba['duration_formatted'],
                str(ba['visits'])
            )
        console.print(ba_table)

    if score >= 80:
        console.print(Panel.fit(
            "[bold green]Great focus session! Maintain this streak![/bold green]",
            title="Recommendation"
        ))
    elif score >= 50:
        console.print(Panel.fit(
            "[bold yellow]Try reducing interruptions for a better score. "
            "Consider closing distracting apps before your next session.[/bold yellow]",
            title="Recommendation"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]Focus could be improved significantly. "
            "Try shorter sessions with fewer distractions allowed.[/bold red]",
            title="Recommendation"
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
