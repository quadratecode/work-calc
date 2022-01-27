from pywebio import *
from pywebio.session import info as session_info
import datetime
from dateutil.easter import *
import arrow
import plotly.express as px
import pandas as pd
import logging

#§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§#

# ~~ LICENSE (EN) ~~

# Copyrighted, Roger Meier 2021

# Licensed under the EUPL-1.2 only, with the specific provisions (EUPL-1.2 articles 14 and 15)
# that the applicable law is the Swiss law and the Jurisdiction Zürich, Switzerland.
# Any redistribution must include the specific provisions above.

# You should have received a copy of the EUPL-1.2 along with this code.
# If not, see <https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12>.


# ~~ LIZENZ (DE) ~~

# Urheberrechtlich geschützt, Roger Meier 2021

# Lizenziert unter der EUPL, nur Version 1.2, mit der vorrangigen Bestimmung (Art. 14 und 15 EUPL-1.2),
# dass diese Lizenz dem schweizerischen Recht untersteht und der Gerichtsstand Zürich, Schweiz, ist.
# Jegliche Weiterverbreitung muss die vorgenannten Bestimmungen beinhalten.

# Zusammen mit diesem Code solten Sie eine Kopie der EUPL-1.2 erhalten haben.
# Andernfalls siehe <https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12>.

#§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§#


# Custom config
config(title="Employment Termination Calculator | Kündigungsrechner",
      description="Automatically calculate embargo periods, sick pay and notice periods according to Swiss law. | Eine Webapplikation zur automatischen Berechnung von Kündigungs-, Sperr- und Lohnfortzahlungsfristen nach Schweizer Recht.",
      css_style="""
        #input-container,
        #output-container,
        .pywebio {
            background:#fafafa
        }
        
        .footer {
            display: none
        }
        
        .input-container,
        .form-group {
            margin-bottom: 30px
        }
        
        label {
        font-weight: 500
        }

        input::-webkit-calendar-picker-indicator {
            display: none;
        }

        input[type="date"]::-webkit-input-placeholder { 
            visibility: hidden !important;
        }
        """)


# --- FUNCTIONS --- #

# Function to choose language according to browser language
def lang(eng, german):
    if 'de' in session_info.user_language:
        return german
    else:
        return eng

# Function to validate form data
def check_form(data):
    if data.get("employment_sdt") > data.get("termination_dt"):
        return ("termination_dt", lang("ERROR: The date of termination of your employment cannot be older than its beginning.", "ERROR: Das Kündigungsdatum kann nicht vor dem Startdatum liegen."))
    if data.get("incapacity_1_sdt") > data.get("incapacity_1_edt"):
        return ("incapacity_1_edt", lang("ERROR: The end of your incapacity cannot be older than its beginning.", "ERROR: Das Enddatum der Arbeitsfähigkeit kann nicht vor ihrem Startdatum liegen."))
    if len(data.get("workdays")) < 5:
        return ("workdays", lang("ERROR: This calculator only supports 100% workload. Please choose 5 days or more.", "ERROR: Dieser Rechner kann nur Vollzeitarbeit evaluieren. Bitte wählen Sie mind. 5 Tage."))
    

# Funtion to validate checkbox
def check_tc(terms):
    if not lang("I accept the terms and conditions", "Ich akzeptiere die Nutzungsbedingungen.") in terms:
        return (lang("ERROR: You must accept the terms and conditions to continue.", "ERROR: Um fortzufahren müssen die Nutzungsbedingungen akzeptiert werden."))

# Function to calculate overlap between two date ranges
def overlap_calc(sdt_1, sdt_2, edt_1, edt_2):
        latest_start = max(sdt_1, sdt_2)
        earliest_end = min(edt_1, edt_2)
        delta = (earliest_end.date() - latest_start.date()).days + 1
        overlap = max(0, delta)
        return(overlap)

# Function to push dates to desired endpoint
def push_endpoint(date, endpoint):
    if endpoint in ["No mention of termination date", "Keine Angaben zum Kündigungstermin", "Termination date only end of month", "Kündigungstermin nur auf Ende Monat"]:
        return date.ceil("month") # push to the end of the month
    elif endpoint in ["Termination date only end of week", "Kündungstermin nur auf Ende Woche"]:
        return date.ceil("week") # push to the end of the week
    elif endpoint in ["Termination date only end of quarter", "Kündungstermin nur auf Ende Quartal"]:
        return date.ceil("quarter") # push to the end of the quarter
    elif endpoint in ["Termination date only end of year", "Kündungstermin nur auf Ende Jahr"]:
        return date.ceil("year") # push to the end of the year
    else:
        return date

# Function to evaluate service year thresholds
def get_last_index(list_of_elems, condition, default_idx=-1) -> int:
    try:
        return next(i for i in range(len(list_of_elems) - 1, -1, -1)
                    if condition(list_of_elems[i]))
    except StopIteration:  # no date earlier than comparison date is found
        return default_idx

# Function to calculate time period duration in days
def period_duration(start_date, end_date):
    return (end_date - start_date).days + 1
    
# Function to correct single dates
def single_date(lst, first_index, last_index):
    if lst[first_index] > lst[last_index]:
        lst[first_index] = lst[last_index]
        return lst

# Function to check if index exists
def check_index(lst, index):
    if index < len(lst):
        return lst[index]
    else:
        lst.insert(index, "")
        return lst[index]

# Function to check if a given date is a holiday
# Source: https://www.bj.admin.ch/dam/bj/de/data/publiservice/service/zivilprozessrecht/kant-feiertage.pdf
def holiday_checker(day, workplace):
    easter_dt = arrow.Arrow.fromdate(easter(day.year))
    if (
        # Neujahrstag (all cantons)
        (day == arrow.Arrow(day.year, 1, 1))
        # Berchtoldstag
        or (day == arrow.Arrow(day.year, 1, 2) and workplace in ["ZH", "BE", "LU", "OW", "NW", "GL", "ZG", "FR", "SO", "SH", "SG", "AG", "TG", "VD", "VS", "NE", "JU"])
        # Heilige Drei Könige
        or (day == arrow.Arrow(day.year, 1, 6) and workplace in ["UR", "SZ", "TI"])
        # Jahrestag der Ausrufung der Republik Neuenburg
        or (day == arrow.Arrow(day.year, 3, 1) and workplace in ["NE"])
        # Josefstag
        or (day == (arrow.Arrow(day.year, 3, 19) and workplace in ["UR", "SZ", "NW", "SO", "TI", "VS"]))
        # Karfreitag
        or (day == easter_dt.shift(days=-2) and workplace in ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", "VD", "NE", "GE", "JU"])
        # Ostermontag
        or (day == easter_dt.shift(days=+1) and workplace in ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS", "GE", "JU"])
        # Fahrtsfest
        or (day == arrow.Arrow(day.year, 4, 1).shift(weekday=4) and workplace in ["GL"])
        # Tag der Arbeit
        or (day == arrow.Arrow(day.year, 5, 1) and workplace in ["ZH", "BS", "BL", "SH", "AG", "TG", "TI", "NE", "JU"])
        # Auffahrt
        or (day == easter_dt.shift(days=+39) and workplace in ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS", "NE", "GE", "JU"])
        # Pfingstmontag
        or (day == easter_dt.shift(days=+50) and workplace in ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS", "GE", "JU"])
        # Frohnleichnam
        or (day == easter_dt.shift(days=+60) and workplace in ["LU", "UR", "SZ", "OW", "NW", "ZG", "FR","SO", "AI", "AG", "TI", "VS", "NE", "JU"])
        # Commémoration du plébiscite jurassien
        or (day == arrow.Arrow(day.year, 6, 23) and workplace in ["JU"])
        # Peter und Paul
        or (day == arrow.Arrow(day.year, 6, 29) and workplace in ["TI"])
        # Bundesfeier (all cantons)
        or (day == arrow.Arrow(day.year, 8, 1))
        # Mariä Himmelfahrt
        or day == (arrow.Arrow(day.year, 8, 15) and workplace in ["LU", "UR", "SZ", "OW", "NW", "ZG", "FR", "SO", "AI", "AG", "TI", "VS", "JU"])
        # Jeûne genevois
        or (day == arrow.Arrow(day.year, 9, 1).shift(weekday=6).shift(weekday=4) and workplace in ["GE"])
        # Mauritiustag
        or (day == arrow.Arrow(day.year, 9, 25) and workplace in ["AI"])
        # Bruderklausenfest
        or (day == arrow.Arrow(day.year, 9, 25) and workplace in ["OW"])
        # Allerheiligen
        or (day == arrow.Arrow(day.year, 11, 1) and workplace in ["LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "AI", "SG", "AG", "TI", "VS", "JU"])
        # Mariä Empfängnis
        or (day == arrow.Arrow(day.year, 12, 8) and workplace in ["LU", "UR", "SZ", "OW", "NW", "ZG", "FR", "AI", "AG", "TI", "VS"])
        # Weihnachtstag (all cantons)
        or (day == arrow.Arrow(day.year, 12, 25))
        # Stephanstag
        or (day == arrow.Arrow(day.year, 12, 26) and workplace in ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VS", "NE"])
        # Restauration de la République
        or (day == arrow.Arrow(day.year, 12, 31) and workplace in ["GE"])
    ):
        return True
    else:
        return False

# Function to limit a date to be between lower and upper bounds
# Source: https://stackoverflow.com/a/5996949/14819955
def clamp(n, minn, maxn):
    if n < minn:
        return minn
    elif n > maxn:
        return maxn
    else:
        return n


# --- MAIN FNCTION --- #

def main():


    # --- SESSION CONTROL --- #
    session.set_env(input_panel_fixed=False,
                    output_animation=False)


    # --- INPUT --- #
    
    output.put_markdown(lang("""# Employment Termination Calculator (1.0.0-beta.1)""", """# Kündigungsrechner (1.0.0-beta.1)"""))

    with output.use_scope("scope1"):
        output.put_markdown(lang("""
            Have you been terminated from your employment and were you incapacitated prior, during or after due to illness or accident? Use this web app to check the temporal validity of your termination and to calculate any possible embargo and notice periods under Swiss law.
            ""","""
            Ist Ihnen gekündigt worden und waren Sie davor, währenddessen oder danach arbeitsunfähig aufgrund von Krankheit oder Unfall? Mit dieser Webapplikation können Sie die zeitliche Gültigkeit Ihrer Kündigung gemäss Schweizer Recht überprüfen und allfällige Sperr- und Kündigungsfristen berechnen.
            """)).style('margin-top: 20px')

        output.put_markdown(lang("""
            ----
            **This web app is currently undergoing beta testing. Please send me [a message](mailto:rm@llq.ch) with your input data and a screenshot of your results if you suspect them to be incorrect.**
            
            **Please note that not all possible case combinations have been implemented yet – check below for further information.**
            ""","""
            ----
            **Diese Webapplikation befindet sich derzeit in der Betaphase. Bitte senden Sie mir [eine Nachricht](mailto:rm@llq.ch) mit Ihren Fallangaben und der Auswertung, sollten Sie vermuten, dass die Resultate inkorrekt sind.**
            
            **Bitte beachten Sie, dass noch nicht alle möglichen Fallkombinationen implementiert sind – Näheres können Sie den nachfolgenden Informationen entnehmen.**
            """))

        output.put_collapse(lang("Further Information", "Ergänzende Informationen"), [
            output.put_markdown(lang("""
            ### About this App

            This app evaluates:

            - Permanent full-time employment (100 %)
            - Incapacities due to illness or accident
            - The probation period duration incl. a possible extension considering legally mandated holidays
            - The validity of a termination with regards to the embargo period
            - The embargo period duration
            - The notice period duration incl. a possible extension
            - Leap years are respected
            - Changes in seniority during an incapacity are respected
            
            Results are visualized on an interactive timeline.

            ### Case Combinations
            
            This app is able to evaluate cases with a single, connected incapacity.

            **Not possible** is currently the evaluation of the following case combinations:
            
            - Temporary or part-time employment
            - Incapacity due to compulsory military service or similar, pregnancy or participation in overseas aid projects
            - A single incapacity with gaps
            - Multiple incapacities, with or without gaps
            - Contractual agreements that differ from the possible inputs, e.g. different notice periods for a termination during the probation period
            ""","""
            ### Über diese App

            Diese App evaluiert:

            - Unbefristete Arbeitsverhältnisse in Vollzeit (100 %)
            - Arbeitsunfähigkeiten zufolge Krankheit oder Unfall
            - Die Dauer der Probezeit inkl. allfälliger Verlängerung unter Berücksichtigung gesetzlicher Feiertage 
            - Die Gültigkeit der Kündigung im Zusammenhang mit der Sperrfrist
            - Die Dauer der Sperrfrist
            - Die Kündigungsfrist inkl. allfälliger Verlängerung
            - Schaltjahre werden berücksichtigt
            - Wechsel im Dienstalter während einer Arbeitsunfähigkeit werden berücksichtigt
            
            Die Resultate werden auf einem interaktiven Zeitstrahl visualisiert.

            ### Fallkombinationen
            
            Diese App kann Fallkonstellationen evaluieren, bei denen eine einzelne, zusammenhängende Arbeitsunfähigkeit vorliegt.

            **Nicht erfasst** sind derzeit folgende Fallkonstellationen:
            
            - Befristete Arbeitsverhältnisse oder Teilzeit
            - Arbeitsunfähigkeit zufolge obligatorischen Militär- oder Schutzdienstes, Schwangerschaft oder Teilnahme an einer Dienstleistung für eine Hilfsaktion im Ausland
            - Die gleiche Arbeitsunfähigkeit mit Unterbrüchen
            - Mehrere Arbeitsunfähigkeiten, zusammenhängend oder mit Unterbrüchen
            - Vertragliche Vereinbarungen, die von den möglichen Eingaben abweichen, bspw. abweichende Kündigungsfristen bei einer Kündigung in der Probezeit.
            """))]).style('margin-top: 20px')
        
        output.put_collapse(lang("Legal Framework", "Rechtliche Grundlagen",), [
            output.put_html(lang("""
                <ul>
                    <li> Probation Period: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/en#art_335_b">Art. 335b OR</a> </li>
                    <li> Regular Termination: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/en#art_335_c">Art. 335c OR</a> </li>
                    <li> Embargo Period: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/en#art_336_c">Art. 336c OR</a> </li>
                    <li> Sick Pay: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/en#art_324_a">Art. 324a OR</a> </li>
                    <li> Federal document on legally mandated holidays: <a target="_blank" rel="noopener noreferrer" href="https://www.bj.admin.ch/dam/bj/de/data/publiservice/service/zivilprozessrecht/kant-feiertage.pdf">Link to PDF</a> </li>
                </ul>
            """,
            """
                 <ul>
                    <li> Probezeit: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_335_b">Art. 335b OR</a> </li>
                    <li> Ordentliche Kündigung: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_335_c">Art. 335c OR</a> </li>
                    <li> Sperrfristen: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_336_c">Art. 336c OR</a> </li>
                    <li> Lohnfortzahlung: <a target="_blank" rel="noopener noreferrer" href="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_324_a">Art. 324a OR</a> </li>
                    <li> Dokument des Bundes über die gesetzlichen Feiertage: <a target="_blank" rel="noopener noreferrer" href="https://www.bj.admin.ch/dam/bj/de/data/publiservice/service/zivilprozessrecht/kant-feiertage.pdf">Link to PDF</a> </li>
                </ul>
            """))]).style('margin-top: 20px')

        output.put_collapse((lang("Technical Information", "Technisches")), [
            output.put_markdown(lang("""
            
            Only optimized for modern browsers and screens above 1080p in width.

            Built with PyWebIO[1] and published under the EUPL (v1.2 only) on GitHub[2].

            ""","""
            
            Nur für moderne Browser und Bildschirme mit einer Breite von über 1080p optimiert.

            Erstellt mit PyWebIO[1] und veröffentlicht unter der EUPL (nur v1.2) auf GitHub[2].
            """)),
            output.put_html("""
                <a target="_blank" href="https://www.pyweb.io/">[1] PyWebIO</a> <br>
                <a target="_blank" href="https://github.com/quadratecode/ch-termination-calc">[2] GitHub Repository</a>
            """)]).style('margin-top: 20px')

        output.style(output.put_markdown(lang("""
            ## Terms and Conditions

            **This web application is provided "as is". Use at your own risk. Warranties or liabilities of any kind, including for technical defects, are excluded to the extent permitted by applicable law. Always double check your results manually and do not rely solely on the automatically generated evaluation.**
            ""","""
            ## Nutzungsbedingungen

            **Diese Webanwendung wird im Ist-Zustand zur Verfügung gestellt. Die Nutzung erfolgt auf eigene Gefahr. Jegliche Sachgewährleistung und jegliche Haftung, inkl. der Haftung für technische Mängel, ist im gesetzlich zulässigen Umfang ausgeschlossen. Ihre Resultate sollten Sie stets von Hand nachprüfen. Verlassen Sie sich nicht ausschliesslich auf das automatisch generierte Ergebnis.**
            """)), "color:crimson")
    
    terms = input.checkbox(options=[lang("I accept the terms and conditions", "Ich akzeptiere die Nutzungsbedingungen.")], validate=check_tc)

    with output.use_scope("scope1", clear=True):
        output.put_markdown("""""") # empty scope1

    data = input.input_group(lang("Your Input", "Ihr Input"), [
        # Employment start date
        input.input(
            lang(
                "On which date was your first day on the job?",
                "An welchem Datum haben Sie Ihre Stelle angetreten?"),
            name="employment_sdt",
            type=input.DATE,
            required=True),
        # Working Days
        input.checkbox(
                lang("Which weekdays do you work on?", "An welchen Wochentagen arbeiten Sie?"),
                ["Montag / Monday", "Dienstag / Tuesday", "Mittwoch / Wednesday", "Donnerstag / Thursday", "Freitag / Friday", "Samstag / Saturday", "Sonntag / Sunday"],
                name="workdays",
                required=True),
        # probation period
        input.select(
            lang(
                "What is the duration of the probation period according to your employment contract (in months)?",
                "Wie lange dauert die Probezeit gemäss Ihrem Arbeitsvertrag (in Monaten)?"),
                [lang(
                    "No mention of probation period",
                    "Keine Angaben zur Probezeit"),
                    "1", "2", "3",
                lang(
                    "No probation period",
                    "Keine Probezeit")],
                name="prob_period_input",
                type=input.TEXT,
                required=True),
        # Date of termination
        input.input(
            lang(
                "On which date did you receive your notice of termination?",
                "An welchem Datum haben Sie Ihre Kündigung erhalten?"),
            name="termination_dt",
            type=input.DATE,
            required=True),
        # Start of incapacity
        input.input(
            lang(
                "When did your incapacity for work start?",
                "An welchem Datum hat Ihre Arbeitsunfähigkeit begonnen?"),
                name="incapacity_1_sdt",
                type=input.DATE,
                required=False),
        # End of incapacity
        input.input(lang("When did your incapacity for work end?", "An welchem Datum hat Ihre Arbeitsunfähigkeit geendet?"),
            name="incapacity_1_edt",
            type=input.DATE,
            required=False),
        # Duration of notice period
        input.select(
            lang(
                "What is the duration of the notice period according to your employment contract (in months)?",
                "Wie lange dauert die Kündigungsfrist gemäss Ihrem Arbeitsvertrag (in Monaten)?"),
            [lang(
                "No mention of notice period",
                "Keine Angaben zur Kündigungsfrist"),
                "1", "2", "3", "4", "5", "6", "7", "8","9", "10", "11", "12"],
            name="notice_period_input",
            type=input.TEXT,
            required=True),
        # Cancellation end of month required
        input.select(
            lang(
                "Which possible termination date is specified in your employment contract?",
                "Auf welchen Termin erlaubt Ihr Arbeitsvertrag die Kündigung?"),
            [lang(
                "No mention of termination date",
                "Keine Angaben zum Kündigungstermin"),
            lang(
                "Termination date only end of week",
                "Kündungstermin nur auf Ende Woche"),
            lang(
                "Termination date only end of month",
                "Kündigungstermin nur auf Ende Monat"),
            lang(
                "Termination date only end of quarter",
                "Kündungstermin nur auf Ende Quartal"),
            lang(
                "Termination date only end of year",
                "Kündungstermin nur auf Ende Jahr"),
            lang(
                "Termination date anytime",
                "Kündungstermin jederzeit")],
            name="endpoint",
            type=input.TEXT,
            required=True),
            input.select(
                lang("In which canton do you work?", "In welchem Kanton arbeiten Sie?"),
                ["AG", "AI", "AR", "BS", "BL", "BE", "FR", "GE", "GL", "GR", "JU", "LU", "NE", "NW",
                "OW", "SH", "SZ", "SO", "SG", "TG", "TI", "UR", "VS", "VD", "ZG", "ZH"],
                name="workplace",
                type=input.TEXT,
                required=True),
        # Place of work
    ], validate = check_form)


    # --- VARIABLES AND LISTS FROM USER INPUT --- #

    # Declare variables
    employment_sdt = arrow.get(data.get("employment_sdt"))
    termination_dt = arrow.get(data.get("termination_dt"))
    prob_period_input = data.get("prob_period_input") # Trail period duration
    notice_period_input = data.get("notice_period_input") # Notice period duration
    endpoint = data.get("endpoint") # Allowed termination end date
    workplace = data.get("workplace") # Place of work

    # Initiatie lists, structure: unequal indicies indicate start dates, equal ones end dates (starts from index 0)
    try:
        incapacity_1_lst = [arrow.get(data.get("incapacity_1_sdt")), arrow.get(data.get("incapacity_1_edt"))]
    except arrow.parser.ParserError:
        incapacity_1_lst = []
    reg_employment_lst = [employment_sdt, termination_dt]
    prob_period_lst = [employment_sdt]
    embargo_1_lst = []
    gap_1_lst = []
    notice_period_lst = []
    extension_lst = []
    sick_pay_lst = []
    master_lst = [reg_employment_lst, prob_period_lst, incapacity_1_lst, embargo_1_lst, gap_1_lst, notice_period_lst, extension_lst, sick_pay_lst]
    workdays_input = data.get("workdays")
    workdays_num = []
    missed_workdays = []
    repeated_workdays = []
    holidays = []

    # Gather weekday numbers from user input
    # Source: https://stackoverflow.com/a/70202124/14819955
    weekday_mapping = {day: index for index, day in enumerate((
    "Montag / Monday", "Dienstag / Tuesday", "Mittwoch / Wednesday", "Donnerstag / Thursday", "Freitag / Friday", "Samstag / Saturday", "Sonntag / Sunday"))}
    for weekday in workdays_input:
        workdays_num.append(weekday_mapping.get(weekday, weekday))


    # --- PROBATION PERIOD --- #

    # Extract probation period from user input
    if prob_period_input in ["No mention of probation period", "Keine Angaben zur Probezeit"]:
        prob_period_dur = 1
    elif prob_period_input in ["No probation period", "Keine Probezeit"]:
        prob_period_dur = 0
        prob_period_lst.clear()
    else:
        prob_period_dur = int(prob_period_input)

    try:
        # Calculate probation period end date
        prob_period_lst.insert(1, min(prob_period_lst[0].shift(months=+prob_period_dur, days=-1), termination_dt)) # BGer 4C.45/2004
        
        # Gather future holidays for 2 years
        for day in arrow.Arrow.range("days", prob_period_lst[0], limit=730):
            if holiday_checker(day, workplace) == True:
                holidays.append(day)

        # Extend probation period if incapacity occured during original probation period
        if prob_period_lst[1] > incapacity_1_lst[0]:
            
            # Gather working days during probation period
            for day in arrow.Arrow.range("days", max(prob_period_lst[0], incapacity_1_lst[0]), min(prob_period_lst[1], incapacity_1_lst[1])):
                if (day.weekday() in workdays_num) and (day not in holidays):
                    missed_workdays.append(day)

            # Create probtion period extension start date
            prob_period_lst.insert(2, prob_period_lst[1].shift(days=+1))

            # Gather working days during probation period extension and match against amount of missed working days
            for day in arrow.Arrow.range("days", max(prob_period_lst[1], incapacity_1_lst[1]).shift(days=+1), limit=365):
                if (day.weekday() in workdays_num) and (day not in holidays) and (len(missed_workdays) > len(repeated_workdays)):
                    repeated_workdays.append(day)

            # Set extension end date
            prob_period_lst.insert(3, min(repeated_workdays[-1], termination_dt)) # cap at termination

            # Match start and end date
            single_date(prob_period_lst, 2, 3)
        
        # Shift regular employment start date
        reg_employment_lst[0] = prob_period_lst[-1].shift(days=+1)

    except IndexError as e:
        logging.critical(e, exc_info=True)
        pass


    # --- TERMINATION AND NOTICE PERIOD --- #

    # Create list with seniority thresholds
    syears = []
    for i in range(0,35):
        syears.append(employment_sdt.shift(years=i))

    # Legal minimum notice period according to seniority
    if notice_period_input in ["No mention of notice period", "Keine Angaben zur Kündigungsfrist"]:
        if termination_dt < syears[1]:
            notice_period = 1
        elif termination_dt >= syears[5]:
            notice_period = 3
        else:
            notice_period = 2
    else:
        notice_period = int(notice_period_input)

    # Calculate regular employment period end date
    reg_employment_lst[1] = push_endpoint(reg_employment_lst[1], endpoint)

    # Determine notice period start date (BGE 134 III 354)
    notice_period_lst.insert(0, reg_employment_lst[1].shift(days=1))

    # Determine notice period end date
    notice_period_lst.insert(1, reg_employment_lst[1].shift(months=+notice_period))

    # Push notice period end date if required
    notice_period_lst[1] = push_endpoint(notice_period_lst[1], endpoint)

    # Backwards check of notice period duration, truncate
    while notice_period_lst[0].shift(months=+notice_period) < notice_period_lst[1]:
        notice_period_lst[0] = notice_period_lst[0].shift(months=+1)
        reg_employment_lst[1] = notice_period_lst[0].shift(days=-1)

    # Calculate new employment end date
    new_employment_edt = notice_period_lst[-1]


    # --- INCAPACITY AND EMBARGO PERIOD --- #

    # Conditions necessitating an embargo period
    if reg_employment_lst[0] <= incapacity_1_lst[1]:
        embargo_1_lst.insert(0, max(reg_employment_lst[0], incapacity_1_lst[0])) # starts on the same day
    else:
        embargo_1_lst.clear()
        embargo_total_dur = 0
        total_notice_overlap = 0

    try:
        # Set embargo period end date according to seniority
        if embargo_1_lst[0] < syears[1]:
            embargo_1_lst.insert(1, min(embargo_1_lst[0].shift(days=29), incapacity_1_lst[1])) # cap at 30 days incl. start and end date
        elif embargo_1_lst[0] >= syears[5]:
            embargo_1_lst.insert(1, min(embargo_1_lst[0].shift(days=179), incapacity_1_lst[1])) # cap at 180 days incl. start and end date
        else:
            embargo_1_lst.insert(1, min(embargo_1_lst[0].shift(days=89), incapacity_1_lst[1])) # cap at 90 days

        # Split embargo period if seniority threshold is crossed during embargo period
        if syears[1].is_between(embargo_1_lst[0], incapacity_1_lst[1], "[)"):
            embargo_1_lst[1] = min(embargo_1_lst[0].shift(days=29), syears[1].shift(days=-1))
            embargo_reset_dur_1 = period_duration(embargo_1_lst[0], embargo_1_lst[1])
            embargo_1_lst.insert(2, syears[1])
            embargo_1_lst.insert(3, min(embargo_1_lst[2].shift(days=(89 - embargo_reset_dur_1)), incapacity_1_lst[1]))
            embargo_reset_dur_2 = period_duration(embargo_1_lst[2], embargo_1_lst[3])
        elif syears[5].is_between(embargo_1_lst[0], incapacity_1_lst[1], "[)"):
            embargo_1_lst[1] = min(embargo_1_lst[0].shift(days=89), syears[5].shift(days=-1))
            embargo_reset_dur_1 = period_duration(embargo_1_lst[0], embargo_1_lst[1])
            embargo_1_lst.insert(2, syears[5])
            embargo_1_lst.insert(3, min(embargo_1_lst[2].shift(days=(179 - embargo_reset_dur_1)), incapacity_1_lst[1]))
            embargo_reset_dur_2 = period_duration(embargo_1_lst[2], embargo_1_lst[3])
        else:
            embargo_reset_dur_1 = period_duration(embargo_1_lst[0], embargo_1_lst[1])
            embargo_reset_dur_2 = 0

        # Calculate total embargo dur
        embargo_total_dur = embargo_reset_dur_1 + embargo_reset_dur_2

        # Calculate notice overlap of first embargo period
        notice_overlap_1 = overlap_calc(notice_period_lst[0], embargo_1_lst[0], notice_period_lst[1], embargo_1_lst[1])

        # Handle cases where the embargo period was split
        if embargo_reset_dur_2 != 0:
            
            # Insert gap period between end of first embargo period and start of second embargo period
            gap_1_lst.insert(0, embargo_1_lst[1].shift(days=1))
            gap_1_lst.insert(1, embargo_1_lst[2].shift(days=-1))
            gap_dur = period_duration(gap_1_lst[0], gap_1_lst[1])

            # Calculate overlap of second embargo period
            notice_overlap_2 = overlap_calc(notice_period_lst[0], embargo_1_lst[2], notice_period_lst[1], embargo_1_lst[3])

            # Compare overlap with gap duration
            # Delete second embargo period total overlap fits into gap
            if notice_overlap_1 + notice_overlap_2 <= gap_dur and termination_dt < embargo_1_lst[1]:
                 del embargo_1_lst[2:]
                 notice_overlap_2 = 0
        else:
            notice_overlap_2 = 0

        # Calculate total notice overlap
        total_notice_overlap = notice_overlap_1 + notice_overlap_2

        # Shift missed notice period days, start and end date
        if total_notice_overlap != 0:
            notice_shift = total_notice_overlap
            notice_period_lst.insert(2, max(notice_period_lst[1], embargo_1_lst[-1]).shift(days=+1))
            notice_period_lst.insert(3, max(notice_period_lst[1], embargo_1_lst[-1]).shift(days=+notice_shift))
            single_date(notice_period_lst, 2, 3)

        # Create extension if needed
        if not endpoint in ["Termination date anytime", "Kündigungstermin jederzeit"]:
            extension_lst.insert(0, notice_period_lst[-1].shift(days=+1))
            extension_lst.insert(1, push_endpoint(notice_period_lst[-1], endpoint))
            single_date(extension_lst, 0, 1)
            new_employment_edt = extension_lst[-1]
        else:
            new_employment_edt = notice_period_lst[-1]

    except IndexError as e:
        logging.critical(e, exc_info=True)
        pass


    # --- SICK PAY --- #

    # Sick pay matrix, starting after first year of service
    # Source: https://www.gerichte-zh.ch/themen/arbeit/waehrend-arbeitsverhaeltnis/arbeitsverhinderung/krankheit-und-unfall.html
    pay_matrix = [
        ["", 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42], # ZH (weeks)
        ["", 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6, 6 ,6, 6, 6 ,6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6], # BS / BL (months)
        ["", 1, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6 ,6, 6, 6 ,6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6], # BE (months)
    ]

    # Choose row according to user input
    if workplace in ["ZH", "SH", "TG"]:
        canton = 0
        unit = "weeks"
    elif workplace in ["BS", "BL"]:
        canton = 1
        unit = "months"
    else:
        canton = 2
        unit = "months"

    # Define sick pay start date
    sick_pay_lst.insert(0, max(employment_sdt.shift(months=3), incapacity_1_lst[0]))

    # Calculate seniority at the beginning of the incapacity
    # Source: https://stackoverflow.com/a/70038244/14819955
    sick_pay_syear_start_index = get_last_index(syears, lambda x: x < sick_pay_lst[0])

    # Calculate sick pay according to service year
    if sick_pay_lst[0] < syears[1]:
        sick_pay_lst.insert(1, sick_pay_lst[0].shift(weeks=+3, days=-1))
    else:
        sick_pay_lst.insert(1, sick_pay_lst[0].shift(**{unit:(pay_matrix[canton][sick_pay_syear_start_index])}, days=-1))

    # Cap sick pay end date
    sick_pay_lst[1] = clamp(sick_pay_lst[1], sick_pay_lst[0], min(new_employment_edt, incapacity_1_lst[-1]))

    # Calculate seniority at the end of the incapacity
    sick_pay_syear_end_index = get_last_index(syears, lambda x: x < incapacity_1_lst[1])

    # Compare seniority at start and end
    if sick_pay_syear_start_index == sick_pay_syear_end_index: # in the same year
        sick_pay_reset_dur_1 = period_duration(sick_pay_lst[0], sick_pay_lst[1])
        sick_pay_reset_dur_2 = 0
    else:
        sick_pay_lst[1] = min(sick_pay_lst[1], syears[sick_pay_syear_end_index].shift(days=-1))
        sick_pay_reset_dur_1 = period_duration(sick_pay_lst[0], sick_pay_lst[1])
        sick_pay_lst.insert(2, syears[sick_pay_syear_end_index])
        sick_pay_lst.insert(3, sick_pay_lst[2].shift(**{unit:(pay_matrix[canton][sick_pay_syear_end_index])}, days=-1))
        sick_pay_lst[3] = clamp(sick_pay_lst[3], sick_pay_lst[2], min(new_employment_edt, incapacity_1_lst[-1]))
        sick_pay_reset_dur_2 = period_duration(sick_pay_lst[2], sick_pay_lst[3])

    # Calculate total sick pay duration
    total_sick_pay_dur = sick_pay_reset_dur_1 + sick_pay_reset_dur_2


    # --- EVALUATION --- #

    # Standard case
    termination_case = "standard_case"
    termination_validity = lang("✔️ Your termination appears valid.", "✔️ Ihre Kündigung scheint gültig zu sein.")
    
    # Termination during prbation period
    try:
        if termination_dt.is_between(prob_period_lst[0], prob_period_lst[-1], "[]"):
            termination_case = "prob_case"
    except IndexError as e:
        logging.critical(e, exc_info=True)
        pass
    
    # Termintaion between embargo periods
    try:
        if termination_dt.is_between(embargo_1_lst[0], embargo_1_lst[1], "[]") and not termination_dt.is_between(employment_sdt, prob_period_lst[-1], "[]"):
            termination_case = "embargo_case"
    except IndexError as e:
        logging.critical(e, exc_info=True)
        pass
    try:
        if termination_dt.is_between(embargo_1_lst[2], embargo_1_lst[3], "[]") and not termination_dt.is_between(employment_sdt, prob_period_lst[-1], "[]"):
            termination_case = "embargo_case"
    except IndexError as e:
        logging.critical(e, exc_info=True)
        pass


    # --- Case: TERMINATION DURING PROBATION PERIOD --- #

    # Adjust varibles
    if termination_case == "prob_case":
        notice_period_lst[0] = termination_dt.shift(days=+1)
        notice_period_lst[1] = termination_dt.shift(days=+7)
        del notice_period_lst[2:]
        total_notice_overlap = 0
        reg_employment_lst.clear()
        embargo_1_lst.clear()
        extension_lst.clear()
        new_employment_edt = notice_period_lst[-1]

    # Adjust sick pay
    try:
        if (sick_pay_lst[-1] > new_employment_edt) and sick_pay_reset_dur_2 != 0:
            sick_pay_lst[3] = clamp(sick_pay_lst[3], sick_pay_lst[2], min(new_employment_edt, incapacity_1_lst[-1]))
            sick_pay_reset_dur_2 = period_duration(sick_pay_lst[2], sick_pay_lst[3])
            total_sick_pay_dur = sick_pay_reset_dur_1 + sick_pay_reset_dur_2
        # Cap first sick pay period
        elif (sick_pay_lst[-1] > new_employment_edt) and (sick_pay_reset_dur_2 == 0):
            sick_pay_lst[1] = clamp(sick_pay_lst[1], sick_pay_lst[0], min(new_employment_edt, incapacity_1_lst[-1]))
            sick_pay_reset_dur_1 = period_duration(sick_pay_lst[0], sick_pay_lst[1])
            total_sick_pay_dur = sick_pay_reset_dur_1
    except IndexError as e:
        logging.critical(e, exc_info=True)
        pass

    
    # --- SICK PAY CORRECTION --- #

    # Delete sick pay
    try:
        # Delete sick pay reset period if employment ended before service year threshold
        if new_employment_edt <= syears[sick_pay_syear_end_index]:
            del sick_pay_lst[2:]
            sick_pay_reset_dur_2 = 0
        
        # Delete sick pay if employment or incapacity ended before start of sick pay
        if total_sick_pay_dur < 0:
            sick_pay_lst.clear()
            sick_pay_reset_dur_1 = 0
            sick_pay_reset_dur_2 = 0
            total_sick_pay_dur = 0
    except IndexError as e:
        logging.critical(e, exc_info=True)
        pass


    # --- TERMINATION DURING EMBARGO PERIOD --- #

    if termination_case == "embargo_case":
        termination_validity = lang("❌ YOUR TERMINATION APPEARS INVALID.", "❌ IHRE KÜNDIGUNG SCHEINT UNGÜLTIG ZU SEIN.")
        notice_period_lst.clear()
        total_notice_overlap = 0
        reg_employment_lst[1] = reg_employment_lst[1].shift(years=+10) # showing that employment continues
        extension_lst.clear()
        new_employment_edt = ""
    else:
        pass


    # --- DATE CONVERSION AND OUTPUT PREPARATION --- #

    # Convert lists
    for lst in master_lst:
        for index, value in enumerate(lst):
            if isinstance(value, arrow.Arrow):
                lst[index] = value.datetime.date()

    # Copy local variables and covert to datetime
    local_vars = locals()
    output_dict = local_vars.copy()
    for key, value in list(output_dict.items()):
        if isinstance(value, arrow.Arrow):
            output_dict[key] = value.datetime.date()


    # --- VISUALIZATION --- #

    df = pd.DataFrame([
        dict(Task="[PH_T]", Start=output_dict["termination_dt"], End=output_dict["termination_dt"], Stack="stack_1"), # Placeholder Top
        dict(Task=lang("Sick Pay", "Lohnfortzahlung"), Start=check_index(sick_pay_lst, 0), End=check_index(sick_pay_lst, 1), Stack="stack_2"),
        dict(Task=lang("Sick Pay", "Lohnfortzahlung"), Start=check_index(sick_pay_lst, 2), End=check_index(sick_pay_lst, 3), Stack="stack_2"),
        dict(Task=lang("Probation Period", "Probezeit"), Start=check_index(prob_period_lst, 0), End=check_index(prob_period_lst, 1), Stack="stack_3"),
        dict(Task=lang("Probation Period Extension", "Verlängerung Probezeit"), Start=check_index(prob_period_lst, 2), End=check_index(prob_period_lst, 3), Stack="stack_3"),
        dict(Task=lang("Regular Employment", "Reguläre Anstellung"), Start=check_index(reg_employment_lst, 0), End=check_index(reg_employment_lst, 1), Stack="stack_3"),
        dict(Task=lang("Regular Notice Period", "Ordentliche Kündigungsfrist"), Start=check_index(notice_period_lst, 0), End=check_index(notice_period_lst, 1), Stack="stack_3"),
        dict(Task=lang("Compensation Missed Notice Period", "Kompensation verpasste Kündigungsfrist"), Start=check_index(notice_period_lst, 2), End=check_index(notice_period_lst, 3), Stack="stack_3"),
        dict(Task=lang("Embargo Period", "Sperrfrist"), Start=check_index(embargo_1_lst, 0), End=check_index(embargo_1_lst, 1), Stack="stack_3"),
        dict(Task=lang("Embargo Period", "Sperrfrist"), Start=check_index(embargo_1_lst, 2), End=check_index(embargo_1_lst, 3), Stack="stack_3"),
        dict(Task=lang("Notice Period Extension", "Verlängerung Kündigungsfrist"), Start=check_index(extension_lst, 0), End=check_index(extension_lst, 1), Stack="stack_3"),
        dict(Task=lang("Incapacity", "Arbeitsunfähigkeit"), Start=check_index(incapacity_1_lst, 0), End=check_index(incapacity_1_lst, 1), Stack="stack_4"),
        dict(Task="[PH_B]", Start=output_dict["termination_dt"], End=output_dict["termination_dt"], Stack="stack_5"), # Placeholder Bottom
    ])

    fig = px.timeline(df,
                x_start="Start",
                x_end="End",
                y="Stack",
                opacity=1,
                color="Task",
                color_discrete_sequence=["#ffffff", # Placeholder
                                         "#f032e6", # Sick Pay
                                         "#f58231", # Probation Period
                                         "#42d4f4", # Extension Probation Period
                                         "#3cb44b", # Regular employment
                                         "#000075", # Notice period
                                         "#4363d8", # Compensation missed Notice Period
                                         "#e6194B", # Embargo Period
                                         "#911eb4", # Notice Period Extension
                                         "#800000", # Incapacity 1
                                         "#ffffff"], # Placeholder
                width=1000,
                height=700,
                hover_name="Task",
                hover_data={"Task":False,
                            "Stack":False,
                            "Start": True,
                            "End":True})

    config = {'displayModeBar': True,
              'displaylogo': False,
              'modeBarButtonsToRemove': ['select2d', 'lasso2d']}

    fig.update_traces(marker_line_width=1.0, opacity=0.95)

    fig.update_xaxes(range=[output_dict["employment_sdt"], incapacity_1_lst[1]])

    fig.update_layout(
        barmode="overlay",
        xaxis = dict(
            automargin=True,
            dtick="M1",
            tickformat="%d.%m.%Y",
            type="date",
            showgrid=True,
            rangeslider_visible=True),
        
        margin=dict(
            b=100,
            t=200,),

        yaxis = dict(
            automargin=True,
            visible=False,
            autorange="reversed",
            showgrid=True),
        
        legend=dict(
            title="",
            orientation="h",
            font_size=16,
            x=0,
            y=1.1),

        shapes = [
            dict(
            x0=termination_dt, x1=termination_dt, line_color="#DB162F", fillcolor="#DB162F", y0=0, y1=1, xref='x', yref='paper',
            line_width=3),
            dict(
            x0=syears[1], x1=syears[1], line_color="#3B6728", fillcolor="#3B6728", y0=0, y1=1, xref='x', yref='paper',
            line_width=1.5),
            dict(
            x0=syears[5], x1=syears[5], line_color="#3B6728", fillcolor="#3B6728", y0=0, y1=1, xref='x', yref='paper',
            line_width=1.5),
            dict(
            x0=syears[sick_pay_syear_end_index], x1=syears[sick_pay_syear_end_index], line_color="#3B6728", fillcolor="#3B6728", y0=0, y1=1, xref='x', yref='paper',
            line_width=1.5)],
            
        
        annotations=[
            dict(
            x=termination_dt, y=1, xref='x', yref='paper',font=dict(size=16, color="#DB162F"),
            showarrow=False, xanchor='left', text=lang("Termination", "Kündigung")),
            dict(
            x=syears[1], y=0.05, xref='x', yref='paper',font=dict(size=16, color="#3B6728"),
            showarrow=False, xanchor='left', text="1Y"),
            dict(
            x=syears[5], y=0.05, xref='x', yref='paper',font=dict(size=16, color="#3B6728"),
            showarrow=False, xanchor='left', text="5Y"),
            dict(
            x=syears[sick_pay_syear_end_index], y=0.05, xref='x', yref='paper',font=dict(size=16, color="#3B6728"),
            showarrow=False, xanchor='left', text=str(sick_pay_syear_end_index) + "Y")
            ])


    # --- OUTPUT --- #

    # Reformat dates
    for key, value in list(output_dict.items()):
        if isinstance(value, datetime.date):
            output_dict[key] = value.strftime("%d.%m.%Y")

    for lst in master_lst:
        for index, value in enumerate(lst):
            if isinstance(value, datetime.date):
                lst[index] = value.strftime("%d.%m.%Y")

    # Increase max width for visualization
    session.set_env(output_max_width="1080px")

    with output.use_scope("scope1", clear=True):
        output.put_markdown("""## Input"""), None,
        output.put_table([
        [lang("Event", "Ereignis"), lang("Date", "Datum")],
        [lang("Employment Start Date", "Beginn Arbeitsverhältnis"), output_dict["employment_sdt"]],
        [lang("Date of Termination", "Kündigungsdatum"), output_dict["termination_dt"]],
        [lang("Incapacity Start Date", "Beginn Arbeitsunfähigkeit"), incapacity_1_lst[0]],
        [lang("Incapacity End Date", "Ende Arbeitsunfähigkeit"), incapacity_1_lst[1]],
        ])

        output.put_markdown(lang("""## Non-binding Evaluation""", """## Unverbindliche Auswertung""")).style('margin-top: 20px'), None,
        output.put_markdown(lang("""### Embargo and Notice Periods""", """### Kündigungs- und Sperrfristen """)).style('margin-top: 20px'), None,
        output.put_table([
        [lang("Query", "Abfrage"), lang("Result", "Ergebnis")],
        [lang("Validity of Termination:", "Gültigkeit der Kündigung:"), output_dict["termination_validity"]],
        [lang("Original end date of employment:", "Ursprüngliches Enddatum der Anstellung:"), notice_period_lst[1]],
        [lang("Missed Working Days Probation Period:", "Verpasste Arbeitstage Probezeit:"), str(len(missed_workdays)) + lang(" days", " Tage")],
        [lang("Missed Calendar Days Notice Period:", "Verpasste Kalendertage Kündigungsfrist:"), str(total_notice_overlap) + lang(" days", " Tage")],
        [lang("Total Embargo Duration:", "Gesamtdauer Sperrfrist:"), str(embargo_total_dur) + lang(" days", " Tage")],
        [lang("New End Date of Employment:", "Neues Enddatum der Anstellung:"), output_dict["new_employment_edt"]],
        ])

        output.put_markdown(lang("""### Sick Pay""", """### Lohnfortzahlung """)).style('margin-top: 20px'), None,
        output.put_table([
        ["", lang("Start Date", "Anfangsdatum"), lang("End Date", "Enddatum"), lang("Duration", "Dauer")],
        [lang("1. Period:", "1. Periode:"), sick_pay_lst[0], sick_pay_lst[1], str(sick_pay_reset_dur_1) + lang(" days", " Tage")],
        [lang("2. Period:", "2. Periode:"), sick_pay_lst[2], sick_pay_lst[3], str(sick_pay_reset_dur_2) + lang(" days", " Tage")],
        ["Total:", "", "", str(total_sick_pay_dur) + lang(" days", " Tage")]
        ])

        # Plotly output to PyWebIO
        plotly_html = fig.to_html(include_plotlyjs="require", full_html=False, config=config)
        output.put_markdown(lang("""
        ## Interactive Viszualization

        IMPORTANT: The chart below is intended only as a visual aide. Please consult the table above for your results.

        """, """
        ## Interaktive Visualisierung

        WICHTIG: Die nachfolgende Grafik ist nur als visuelle Hilfe gedacht. Ihre Ergebnisse entnehmen Sie bitte der Tabelle hiervor.

        """)).style('margin-top: 20px'), None,
        output.put_collapse(lang("Further Information", "Ergänzende Hinweise",), [
            output.put_markdown(lang("""

            - This visualization ist interactive - use direct control or the control panel on the top right to navigate the chart area or to hide bars.
            - An export of the chart area as PNG is possible via the control panel on the top right.
            - It is currently not possible to visualize single days, e.g. a notice period extension of a single day does not show.

            ""","""
            - Diese Visualisierung ist interaktiv - nutzen Sie die Direktsteuerung oder das Steuerpanel rechts oben um im Diagrammbereich zu navigieren oder Elemente auszublenden.
            - Ein Export als PNG ist über das Steuerpanel rechts oben möglich.
            - Derzeit ist es nicht möglich, einzelne Tage zu visualisieren. Das bedeutet beispielsweise, dass die Verlängerung der Kündigungsfrist um einen einzelnen Tag nicht angezeigt wird.

            """))]).style('margin-top: 20px'), None,
        output.put_html(plotly_html).style("border: 1px solid #dfe2e5")


# --- DEPLOYMENT --- #
if __name__ == '__main__':
    start_server(main, port=41780, host="0.0.0.0", debug=False)
