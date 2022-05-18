from pywebio import *
from pywebio.session import info as session_info
import datetime
from dateutil.easter import *
import arrow
import plotly.express as px
import pandas as pd

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
      description="Automatically calculate embargo periods, sick pay and notice periods according to Swiss law. | Eine Webapplikation zur automatischen Berechnung von Kündigungs-, Sperr- und Lohnfortzahlungsfristen nach Schweizer Recht.")


# --- FUNCTIONS --- #

# Function to choose language according to browser language
def lang(eng, german):
    if 'de' in session_info.user_language:
        return german
    else:
        return eng

# Function to validate termination input
def check_form_termination(data):
    if employment_sdt > arrow.get(data["termination_dt"], "DD.MM.YYYY"):
        output.put_error(lang("ERROR: Please check your date input. The termination date cannot be older than the employment start date.",
                                "ERROR: Bitte überprüfen Sie Ihre Eingabe. Das Kündigungsdatum kann nicht vor dem Startdatum liegen."),
                            closable=True,
                            scope="scope1")
        return ("", "")

# Function to validate illacc input
def check_form_incapacity(data):
    data_lst = []
    for key in data.keys():
        if data[key] != "":
            data_lst.append(data[key])
    if sorted(data_lst) != data_lst:
        output.put_error(lang("ERROR: Please check your date input. The dates must be entered in chronological order (oldest to youngest).",
                                "ERROR: Bitte überprüfen Sie Ihre Eingabe. Die Daten müssen chronologisch sortiert sein (ältestes bis jüngstes)."),
                            closable=True,
                            scope="scope1")
        return ("", "")

# Funtion to validate checkbox
def check_tc(data):
    if not lang("I accept the terms and conditions", "Ich akzeptiere die Nutzungsbedingungen.") in data:
        output.put_error(lang("ERROR: You must accept the terms and conditions to continue.", "ERROR: Bitte akzeptieren Sie die Nutzungsbedingungen."
                                "ERROR: Bitte überprüfen Sie Ihre Eingabe. Die Daten müssen chronologisch sortiert sein (ältestes bis jüngstes)."),
                            closable=True,
                            scope="scope1")
        return ("", "")

def check_box(data):
    if len(data["workdays_input"]) < 1:
        output.put_error(lang("ERROR: Please choose one weekday or more.", "ERROR: Bitte wählen Sie mind. einen Wochentag."),
                            closable=True,
                            scope="scope1")
        return ("", "")

# Function to correct date subtraction if origin month has more days than target month
# See issue 1
def subtract_corr(sdt, edt):
    if sdt.day != edt.day:
        return(edt)
    else:
        edt = edt.shift(days=-1)
        return(edt)

# Function to calculate overlap between two date ranges
def overlap_calc(sdt_1, sdt_2, edt_1, edt_2):
        latest_start = max(sdt_1, sdt_2)
        earliest_end = min(edt_1, edt_2)
        delta = (earliest_end.date() - latest_start.date()).days + 1
        overlap = max(0, delta)
        return(overlap)

# Function to flatten list
# Source: https://stackoverflow.com/a/10824420/14819955
def flatten(container):
    for i in container:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i

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

# Function to populate dict key with sublist of pairs
def populate_dct(in_dct):
    paired_lst = []
    # New dict without empty keys, convert others to arrow object
    new_dct = {}
    for key, value in in_dct.items():
        if in_dct[key] != "":
            new_dct[key] = arrow.get(value, "DD.MM.YYYY")
    # Put values into list
    value_lst = list(new_dct.values())
    while value_lst:
        paired_lst.append(value_lst[:2])
        value_lst = value_lst[2:]
    return paired_lst


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
    
    output.put_markdown(lang("""# Work Incapacity Calculator""", """# Rechner Arbeitsunfähigkeit"""))

    # User info: Landing page
    with output.use_scope("scope1"):
        output.put_markdown(lang("""
            Were you incapacitated to work due to illness, accident, military service or pregnancy?
            Use this app to evaluate:
            - Trial period extensions
            - Notice periods
            - Embargo periods
            - Sick pay claim
            - Validity of termination

            Give it a try!
            ""","""
            Waren Sie wegen Krankheit, Unfall, Militärdienst oder Schwangerschaft arbeitsunfähig?
            Nutzen Sie diese App um Ihren Fall auszuwerten:
            - Verlängerung der Probezeit
            - Kündigungsfristen
            - Sperrfristen
            - Ansprucha uf Lohnfortzahlung
            - Gültigkeit einer Kündigung

            Probieren Sie es aus!
            """)).style('margin-top: 20px')

        output.put_markdown(lang("""
            ----
            **This app is currently undergoing beta testing. Any [Feedback](mailto:rm@llq.ch) is appreciated.**
            
            The following case combinations **cannot** be evaluated:
            - Temporary employment
            - The combination of different kinds of incapacities (e.g. military service and sickness)
            - More than three separate incapacities due to illness or accidents
            - Contractual agreements that differ from the possible inputs
            ""","""
            ----
            **Diese App befindet sich derzeit im Betatest. [Feedback](mailto:rm@llq.ch) ist sehr wilkommen.**
            
            Die folgenden Fallkonstellationen können nicht ausgewertet werden:
            - Befristete Arbeitsverhältnisse
            - Die Kombination von verschiedenartigen Arbeitsunfähigkeiten (bspw. Militärdienst und Krankheit)
            - Mehr als drei getrennte Arbeitsunfähigkeiten zufolge Unfall oder Krankheit
            - Vertragliche Vereinbarungen, die von den möglichen Eingaben abweichen

            """))

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
            
            Only optimized for modern browsers and screens above 1080p in width. The language (DE/EN) is set according to the language in your browser.

            Built with PyWebIO[1] and published under the EUPL (v1.2 only) on GitHub[2].

            ""","""
            
            Nur für moderne Browser und Bildschirme mit einer Breite von über 1080p optimiert. Die Sprache (DE/EN) richtet sich nach den Einstellungen Ihres Browsers.

            Erstellt mit PyWebIO[1] und veröffentlicht unter der EUPL (nur v1.2) auf GitHub[2].
            """)),
            output.put_html("""
                <a target="_blank" href="https://www.pyweb.io/">[1] PyWebIO</a> <br>
                <a target="_blank" href="https://github.com/quadratecode/ch-termination-calc">[2] GitHub Repository</a>
            """)]).style('margin-top: 20px')

        output.put_markdown(lang("""
            ### Terms and Conditions

            This app is provided "as is". Use at your own risk. Warranties or liabilities of any kind are excluded to the extent permitted by applicable law. Do not rely solely on the automatically generated evaluation.
            ""","""
            ### Nutzungsbedingungen

            Diese App wird im Ist-Zustand zur Verfügung gestellt. Die Nutzung erfolgt auf eigene Gefahr und unter Ausschluss jeglicher Haftung, soweit gesetzlich zulässig. Verlassen Sie sich nicht ausschliesslich auf das automatisch generierte Ergebnis.
            """))
    
    # Terms and conditions
    input.checkbox(
        options=[
            lang("I accept the terms and conditions", "Ich akzeptiere die Nutzungsbedingungen.")],
        validate=check_tc)
    # User Info: Employment data (block required)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Employment

            Please enter the date of the first day of work and the place of work.

            Hints:
            - The first day of work can be different from the starting date of the employment contract.
            ""","""
            ### Arbeitsverhältnis

            Bitte tragen Sie das Datum des Stellenantritts und den Arbeitsort ein.

            Hinweise:
            - Der Tag des Stellenantritts kann vom Anfangsdatum des Arbeitsvertrags abweichen.
            """))

    # User Input: Employment data (block required)
    employment_data = input.input_group("", [
        input.input(
            lang(
                "First day of work (DD.MM.YYYY)",
                "Tag des Stellenatritts"),
            name="employment_sdt",
            type=input.TEXT,
            required=True,
            pattern="[0-9]{2}\.[0-9]{2}\.(19|20)\d{2}$",
            maxlength="10",
            minlength="10"),
        input.select(
            lang("Place of work (canton)", "Arbeitsort (Kanton)"),
            ["AG", "AI", "AR", "BS", "BL", "BE", "FR", "GE", "GL", "GR", "JU", "LU", "NE", "NW",
            "OW", "SH", "SZ", "SO", "SG", "TG", "TI", "UR", "VS", "VD", "ZG", "ZH"],
            name="workplace",
            type=input.TEXT,
            required=True),
    ])
    # Variables: Employment data (input required)
    # Make employment start date global for validation
    global employment_sdt
    employment_sdt = arrow.get(employment_data["employment_sdt"], "DD.MM.YYYY")
    workplace = employment_data["workplace"]


    # User info: Case combinations (block required)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Case Combination

            Please select any case options you would like to evaluate.

            Hints:
            - The evaluation of the trial period is advisable, when any incapacity to work occured during the trial period.
            - The evaluation of a termination is advisable, when a termination has already been issued.
            - If termination is not evaluated, the date of today is taken to calculate seniority.
            ""","""
            ### Fallkonstellation

            Bitte wählen Sie Ihre Fallkonstellation aus.

            Hinweise:
            - Die Auswertung der Probezeit ist insb. dann sinnvoll, wenn eine Arbeitsunfähigkeit während der Probezeit aufgetreten ist.
            - Die Auswertung einer Kündigung ist insb. dann sinnvoll, wenn bereits eine Kündigung erfolgt ist.
            - Wird keine Kündigung ausgewertet, richtet sich das Dienstalter nach dem heutigen Datum.
            """))

    # User input: Case combinations (block required)
    case = input.input_group("", [
        input.select(lang("Which type of incapacity would you like to evaluate?", "Welche Art von Arbeitsunfähigkeit möchten Sie auswerten?"),
            options=[{
                "label":lang("accident or illness","Unfall oder Krankheit"),
                "value":"illacc",
                },{
                "label":lang("military or civil service", "Militär, Schutz- oder Zivildienst"),
                "value":"milservice"
                },{
                "label":lang("pregnancy", "Schwangerschaft"),
                "value":"preg"}],
            name="incapacity_type",
            inline=True,
            required=True),
        input.select(lang("Evaluation of tiral period?", "Auswertung der Probezeit?"),
            [lang("Yes", "Ja"), lang("No", "Nein"), lang("I don't know", "Ich weiss nicht")],
            name="trial_relevance",
            required=True),
        input.select(lang("Evaluation of termination?", "Auswertung einer Kündigung?"),
            [lang("Yes", "Ja"), lang("No", "Nein")],
            name="termination_occurence",
            required=True),
    ])
    # Variables: Case combinations (required input)
    incapacity_type = case["incapacity_type"]
    trial_relevance = case["trial_relevance"]
    termination_occurence = case["termination_occurence"]
    # Set end of seniority to today if no termination was issued
    if case.get("termination_occurence") == "No" or "Nein":
        termination_dt = arrow.now()


    # User info: Amount of incapacities (block optional)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Amount of Incapacities

            You have chosen the evaluation of an incapacity to work due to illness(es) or accident(s). Please specify how many **seperate** illnesses or accidents you would like to evaluate.

            Hints:
            - Incapacities to work counts a **seperate**, when there is **no connection** between them. Example: There is no connection between having the flu and a car accident – these would count as seperate.
            - Incapacities to work count **not as seperate**, when there is **any connection** between them. For example: A prolonged cancer treatment with multiple periods of absence would count as a single incapacity.
            - Breaks between single incapacities (e.g. cancer) can be specified in the next step.
            ""","""
            ### Anzahl Arbeitsunfähigkeiten

            Sie haben die Auswertung einer Arbeitsunfähigkeit zufolge Krankheit oder Unfall ausgewählt. Bitte geben Sie an, wie viele **getrennte** Krankheiten oder Unfälle Sie auswerten möchten.

            Hinweise:
            - Arbeitsunfähigkeiten gelten als **getrennt**, wenn zwischen ihnen **keinerlei Verbindung** besteht. Beispiel: Es besteht keine Verbindung zwischen einer Grippeerkrankung und einem Autounfall.
            - Arbeitsunfähigkeiten gelten **nicht als getrennt**, wenn zwischen ihnen eine **irgendwie geartete Verbindung** besteht. Beispiel: Eine langandauernde Krebstherapie mit vielzähligen Abwesenheiten zählt als einzelne Arbeitsunfähigkeit.
            - Unterbrüche zwischen einer einzelnen Arbeitsunfähigkeit können im nächsten Schritt angegeben werden.
            """))

    # User input: Amount of incapacities (block optional)
    if incapacity_type == "illacc":
        illacc_amount = input.select(lang("Amount of seperate illnesses or accidents", "Anzahl getrennter Unfälle oder Krankheiten"),
            options=[{
                "label":lang("One single accident or illness", "Einzelner Unfall oder Krankheit"),
                "value":1
                },{
                "label":lang("Two or more accidents or illnesses", "Zwei oder mehr Unfälle oder Krankheiten"),
                "value":2
                },{
                "label":lang("Three seperate accidents or illnesses", "Drei getrennte Unfälle oder Krankheiten"),
                "value":3}
            ],
            required=True)


    # User info: Trial period (block optional)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Trial Period

            Please specify on which weekdays the 

            Hints:
            - The evaluation of the trial period is advisable, when any incapacity to work occured during the trial period.
            - The evaluation of a termination is advisable, when a termination has already been issued.
            ""","""
            ### Angaben Probezeit

            Bitte wählen Sie Ihre Fallkonstellation aus.

            Hinweise:
            - Die Auswertung der Probezeit ist insb. dann sinnvoll, wenn eine Arbeitsunfähigkeit während der Probezeit aufgetreten ist.
            - Die Auswertung einer Kündigung ist insb. dann sinnvoll, wenn bereits eine Kündigung erfolgt ist.
            """))

    # User input: Trial period (block optional)
    if trial_relevance != ("No" or "Nein"):
        trial_period_data = input.input_group("", [
            input.checkbox(
                    lang("Which weekdays do you work on?", "An welchen Wochentagen arbeiten Sie?"),
                    ["Montag / Monday", "Dienstag / Tuesday", "Mittwoch / Wednesday", "Donnerstag / Thursday", "Freitag / Friday", "Samstag / Saturday", "Sonntag / Sunday"],
                    name="workdays_input",
                    required=True),
            # probation period
            input.select(
                lang(
                    "Duration of probation period (months)?",
                    "Dauer Probezeit (Monate)?"),
                    [lang(
                        "No mention of probation period",
                        "Keine Angaben zur Probezeit"),
                        "1", "2", "3",
                    lang(
                        "No probation period",
                        "Keine Probezeit")],
                    name="trial_input",
                    type=input.TEXT,
                    required=True),
        ], validate = check_box) 
        # Declare variables from trial period
        workdays_input = trial_period_data["workdays_input"]
        trial_input = trial_period_data["trial_input"]


    # User info: First illacc (alternate block)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### First Incapacity - Breaks

            Please specify, 

            Hints:
            - 
            ""","""
            ### Erste Arbeitsunfähigkeit - Unterbrüche

            Sie 

            Hinweise:
            -
            """))

    # User input: First illacc (alternate block)
    if illacc_amount in [1, 2, 3]:
        first_illacc_data = input.input_group("", [
            input.input(
                lang(
                    "Start date of first period",
                    "Anfangsdatum der ersten Periode"),
                name="illacc_sdt_1",
                type=input.DATE,
                required=True),
            input.input(
                lang(
                    "End date of first period",
                    "Enddatum der ersten Periode"),
                name="illacc_edt_1",
                type=input.DATE,
                required=True),
            input.input(
                lang(
                    "Start date of second period",
                    "Anfangsdatum der zweiten Periode"),
                name="illacc_sdt_2",
                type=input.DATE),
            input.input(
                lang(
                    "End date of second period",
                    "Enddatum der zweiten Periode"),
                name="illacc_edt_2",
                type=input.DATE),
            input.input(
                lang(
                    "Start date of third period",
                    "Anfangsdatum der dritten Periode"),
                name="illacc_sdt_3",
                type=input.DATE),
            input.input(
                lang(
                    "End date of third period",
                    "Enddatum der dritten Periode"),
                name="illacc_edt_3",
                type=input.DATE),
            ], validate = check_form_incapacity)
        # Initiate dict of illacc dates
        incap_dct = {}
        # Sort dates into incap dict as list pairs on the first key
        incap_dct[1] = populate_dct(first_illacc_data)


    # User info: Second illacc (block optional)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Second Incapacity - Breaks

            Please specify, 

            Hints:
            - 
            ""","""
            ### Zweite Arbeitsunfähigkeit - Unterbrüche

            Sie 

            Hinweise:
            -
            """))

    # User input: Second illacc (block optional)
    if illacc_amount in [2, 3]:
        second_illacc_data = input.input_group("", [
            input.input(
                lang(
                    "Start date of first period",
                    "Anfangsdatum der ersten Periode"),
                name="illacc_sdt_1",
                type=input.DATE,
                required=True),
            input.input(
                lang(
                    "End date of first period",
                    "Enddatum der ersten Periode"),
                name="illacc_edt_1",
                type=input.DATE,
                required=True),
            input.input(
                lang(
                    "Start date of second period",
                    "Anfangsdatum der zweiten Periode"),
                name="illacc_sdt_2",
                type=input.DATE),
            input.input(
                lang(
                    "End date of second period",
                    "Enddatum der zweiten Periode"),
                name="illacc_edt_2",
                type=input.DATE),
            input.input(
                lang(
                    "Start date of third period",
                    "Anfangsdatum der dritten Periode"),
                name="illacc_sdt_3",
                type=input.DATE),
            input.input(
                lang(
                    "End date of third period",
                    "Enddatum der dritten Periode"),
                name="illacc_edt_3",
                type=input.DATE),
            ], validate = check_form_incapacity)
        # Sort dates into incap dict as list pairs on the second key
        incap_dct[2] = populate_dct(second_illacc_data)


    # User info: Third illacc (block optional)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Third Incapacity - Breaks

            Please specify, 

            Hints:
            - 
            ""","""
            ### Dritte Arbeitsunfähigkeit - Unterbrüche

            Sie 

            Hinweise:
            -
            """))

    # User input: Third illacc (block optional)
    if illacc_amount in [3]:
        third_illacc_data = input.input_group("", [
            input.input(
                lang(
                    "Start date of first period",
                    "Anfangsdatum der ersten Periode"),
                name="illacc_3_sdt_1",
                type=input.DATE,
                required=True),
            input.input(
                lang(
                    "End date of first period",
                    "Enddatum der ersten Periode"),
                name="illacc_3_edt_1",
                type=input.DATE,
                required=True),
            input.input(
                lang(
                    "Start date of second period",
                    "Anfangsdatum der zweiten Periode"),
                name="illacc_3_sdt_2",
                type=input.DATE),
            input.input(
                lang(
                    "End date of second period",
                    "Enddatum der zweiten Periode"),
                name="illacc_3_edt_2",
                type=input.DATE),
            input.input(
                lang(
                    "Start date of third period",
                    "Anfangsdatum der dritten Periode"),
                name="illacc_3_sdt_3",
                type=input.DATE),
            input.input(
                lang(
                    "End date of third period",
                    "Enddatum der dritten Periode"),
                name="illacc_3_edt_3",
                type=input.DATE),
            ], validate = check_form_incapacity)
        # Sort dates into incap dict as list pairs on the second key
        incap_dct[3] = populate_dct(third_illacc_data)



    # User info: Milservice (alternate block)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Militar or Civil Service - Details

            Please specify on which date the service started and on which it ended.

            Hints:
            - 
            ""","""
            ### Militär-, Zivil- oder Schutzdienst

            Bitte geben Sie das Start- und Enddatum des Dienstes an.

            Hinweise:
            -
            """))

    # User input: Milservice (alternate block)
    if incapacity_type == "milservice":
        milservice_data = input.input_group("", [
            # Start of incapacity
            input.input(
                lang(
                    "Start of service",
                    "Dienstbeginn"),
                    name="milservice_sdt",
                    type=input.DATE,
                    required=True),
            # End of incapacity
            input.input(lang(
                "End of service",
                "Dienstende"),
                name="milservice_edt",
                type=input.DATE,
                required=True),
        ], validate = check_form_incapacity)
        # Variables: Milservice
        incap_dct[1] = [arrow.get(milservice_data["milservice_sdt"], "DD.MM.YYYY"), arrow.get(milservice_data["milservice_edt"], "DD.MM.YYYY")]



    # User info: Pregnancy
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Pregnancy - Details

            Please specify on which the pregnancy commenced and on which date the child was born.

            Hints:
            - The federal court has decided in BGE 143 III 21 that the pregnancy begins on the day the egg is fertilised.
            - If the child has not yet been born, enter an approximate date.
            ""","""
            ### Schwangerschaft - Details

            Bitte geben Sie das Datum für den Beginn der Schwangerschaft und das Datum der Niederkunft an.

            Hinweise:
            - Das Bundesgericht hat in BGE 143 III 21 entschieden, dass die Schwangerschaft mit der Befruchtung der Eizelle beginnt.
            - Falls das Kind noch nicht geboren ist, geben Sie ein ungefähres Datum an.
            """))

    # User input: Pregnancy
    if incapacity_type == "preg":
        preg_data = input.input_group("", [
            # Start of incapacity
            input.input(
                lang(
                    "Start date of pregnancy",
                    "Datum des Schwangerschaftsbeginns"),
                    name="preg_sdt",
                    type=input.DATE,
                    required=True),
            # End of incapacity
            input.input(lang(
                    "Date of childbirth",
                    "Datum der Niederkunft"),
                    name="preg_edt",
                    type=input.DATE,
                    required=True),
        ], validate = check_form_incapacity)
        # Variables: Pregnancy
        incap_dct[1] = [arrow.get(preg_data["preg_sdt"], "DD.MM.YYYY"), arrow.get(preg_data["preg_edt"], "DD.MM.YYYY")]


    # User info: Termination (block optional)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Termination

            Please specify on which date the termination was (or shall be) received, the duration of the notice period and the on what end date the emplyment is allowed to be terminated.

            Hints:
            - 
            ""","""
            ### Kündigung

            

            Hinweise:
            -
            """))

    # User input: Termination (block optional)
    if case.get("termination_occurence") == "Yes" or "Ja":
        termination_data = input.input_group("", [
            # Date of termination
            input.input(
                lang(
                    "On which date did you receive your notice of termination?",
                    "An welchem Datum haben Sie Ihre Kündigung erhalten?"),
                name="termination_dt",
                type=input.DATE,
                required=True),
            # Duration of notice period
            input.select(
                lang(
                    "Duration of notice period (months)",
                    "Dauer der Kündigungsfrist (Monate)"),
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
                    "Termination Date",
                    "Kündigungstermin"),
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
        ], validate = check_form_termination)
        # Variables: Termination
        termination_dt = arrow.get(termination_data["termination_dt"], "DD.MM.YYYY")
        notice_period_input = termination_data["notice_period_input"]
        endpoint = termination_data["endpoint"]


    # User info: Trial termination (block optional)
    with output.use_scope("scope1", clear=True):
        output.put_markdown(lang("""
            ### Trial Termination

            You have chosen to evaluate trial period and termination: Please specify the length of the notice period for the trial period (in days).

            Hints:
            - 
            ""","""
            ### Kündigung Probezeit

            Sie wollen Kündigung und Probezeit auswerten: Bitte geben Sie Kündigungsfrist für die Probezeit an (in Tagen).

            Hinweise:
            -
            """))

    # User input: Trial termination (block optional)
    if (termination_occurence == ("Yes" or "Ja")) and (trial_relevance != ("No" or "Nein")):
        termination_data = input.input_group("", [
            # Duration of notice period
            input.select(
                lang(
                    "Duration of notice period (days)",
                    "Dauer der Kündigungsfrist (Tage)"),
                [lang(
                    "No mention of notice period",
                    "Keine Angaben zur Kündigungsfrist"),
                    "1", "2", "3", "4", "5", "6", "7", "8","9", "10", "11", "12","13", "14", "15",
                    "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30"],
                name="trial_notice_input",
                type=input.TEXT,
                required=True),
        ])
        # Variables: Trial termination
        trial_notice_input = termination_data["trial_notice_input"]



    # --- DECLARE KNOWN VARIABLES, LISTS, DICTS --- #

    # List structure: unequal indicies indicate start dates, equal ones end dates (starts from index 0)
    # List manipulation is handled in pairs hereafter
    # List for incapacities initiated above

    # Lists and dicts with known input
    reg_employment_lst = [employment_sdt, termination_dt]
    trial_lst = [employment_sdt]

    # List with seniority thresholds
    # Create correponding sick pay dict
    syears = []
    sick_pay_dct = {}
    for i in range(0,35):
        syears.append(employment_sdt.shift(years=i))
        sick_pay_dct[i] = []

    # Empty lists
    notice_period_lst = []
    extension_lst = []
    workdays_num = []
    missed_workdays = []
    repeated_workdays = []
    holidays = []
    master_lst = []

    # Empty dicts
    embargo_dct = {}
    gap_dct = {}

    # Gather weekday numbers from user input
    # Source: https://stackoverflow.com/a/70202124/14819955
    weekday_mapping = {day: index for index, day in enumerate((
    "Montag / Monday", "Dienstag / Tuesday", "Mittwoch / Wednesday", "Donnerstag / Thursday", "Freitag / Friday", "Samstag / Saturday", "Sonntag / Sunday"))}
    for weekday in workdays_input:
        workdays_num.append(weekday_mapping.get(weekday, weekday))


    # --- PROBATION PERIOD --- #

    # Check if user selected trial period evaluation
    if (trial_relevance != "No" or "Nein") or (trial_input != "No probation period" or "Keine Probezeit"):

        # Extract probation period duration from user input
        if trial_input in ["No mention of probation period", "Keine Angaben zur Probezeit"]:
            trial_dur = 1
        else:
            trial_dur = int(trial_input)

        # Calculate probation period end date
        trial_lst.insert(1, min(trial_lst[0].shift(months=+trial_dur), termination_dt)) # BGer 4C.45/2004
        trial_lst[1] = subtract_corr(trial_lst[0], trial_lst[1])

        # Check if lowest incapacity date lies within probation period
        if trial_lst[1] > min(list(flatten((incap_dct.values())))):
        # Loop through incapacities
            for key, value in incap_dct.items():
                for incap_sublst in value:
                    
                    # Gather future holidays for 2 years
                    for day in arrow.Arrow.range("days", trial_lst[0], limit=730):
                        if holiday_checker(day, workplace) == True:
                            holidays.append(day)
                                    
                    # Gather working days during probation period
                    for day in arrow.Arrow.range("days", max(trial_lst[0], incap_sublst[0]), min(trial_lst[1], incap_sublst[1])):
                        # Add date to list if it is a working day, not a holiday and not already in the list
                        if (day.weekday() in workdays_num) and (day not in holidays) and (day not in missed_workdays):
                            missed_workdays.append(day)

                    # Gather working days during probation period extension and match against amount of missed working days
                    for day in arrow.Arrow.range("days", max(trial_lst[1], incap_sublst[1]).shift(days=+1), limit=365):
                        if (day.weekday() in workdays_num) and (day not in holidays) and (len(missed_workdays) > len(repeated_workdays)):
                            repeated_workdays.append(day)

                    # Set extension end date
                    trial_lst[1] = min(repeated_workdays[-1], termination_dt) # cap at termination
                    
                    # Shift regular employment start date to after trial period
                    reg_employment_lst[0] = trial_lst[-1].shift(days=+1)

        # Count probation period extension
        trial_extension_dur = len(repeated_workdays)

    # --- GENERAL INCAPACITY --- #

    # Copy incap dict keys
    for key, value in incap_dct.items():
        embargo_dct[key] = []
        # Build corresponding gap dict
        gap_dct[key] = []


    # --- CASE: ILLNESS OR ACCIDENT --- #

    # Selected case type
    if incapacity_type == "illacc":

        # --- EMBARGO PERIODS --- #

        # Keep score of embargo balance, sick pay balance and total notice overlap
        embargo_balance = 0
        embargo_cap = 0
        total_notice_overlap = 0

        # Loop through incapacities by incapacity
        for key, value in incap_dct.items():
            for incap_sublst in value:
                while embargo_balance <= embargo_cap:

                    # Continue with next iteration if incapacitiy start date lies before the beginning of employment
                    if reg_employment_lst[0] >= incap_sublst[1]:
                        break

                    # Set embargo cap according to seniority at beginning of incapacity
                    if incap_sublst[0] < syears[1]:
                        embargo_cap = 29 # cap at 29 days incl. start and end date
                    elif incap_sublst[0] >= syears[5]:
                        embargo_cap = 179 # cap at 179 days incl. start and end date
                    else:
                        embargo_cap = 89 # cap at 90 days incl. start and end date

                    # Insert embargo start date
                    embargo_dct[key].insert(0, [max(reg_employment_lst[0], incap_sublst[0])]) # starts on the same day

                    # Insert embargo end date into embargo dict, max date at end of embargo
                    embargo_dct[key].insert(1, min(incap_sublst[0].shift(days=embargo_cap), incap_sublst[1]))

                    # Check if service year 1, 5 is crossed during embargo period
                    if syears[1].is_between(incap_sublst[0], incap_sublst[1], "[)"):
                        crossed_syear = 1
                        new_embargo_cap = 89
                    elif syears[5].is_between(incap_sublst[0], incap_sublst[1], "[)"):
                        crossed_syear = 5
                        new_embargo_cap = 179

                    # Split embargo period if seniority threshold is crossed during embargo period
                    # Put split embargo periods into dict key 11, 12, 13...
                    if crossed_syear != 0:
                        embargo_dct[key][1] = min(embargo_dct[key][0].shift(days=embargo_cap), syears[crossed_syear].shift(days=-1)) # End before split
                        embargo_reset_dur = period_duration(embargo_dct[key][0], embargo_dct[key][1])
                        embargo_dct[key + 10](0, syears[crossed_syear]) # Start after split
                        embargo_dct[key + 10](1, min(embargo_dct[key][2].shift(days=(new_embargo_cap - embargo_reset_dur)), incap_sublst[1])) # End after split

                    # Calculate overlap between embargo period and notice period
                    notice_overlap = overlap_calc(notice_period_lst[0], embargo_dct[key][0], notice_period_lst[1], embargo_dct[key][1])

                    # Clean up cases where the embargo period was split
                    if (key + 10) in embargo_dct.keys():
                        
                        # Insert gap period between end of first embargo period and start of second embargo period
                        gap_dct[key].insert(0, embargo_dct[key][1].shift(days=1))
                        gap_dct[key].insert(1, embargo_dct[key + 10][0].shift(days=-1))
                        gap_dur = period_duration(gap_dct[key][0], gap_dct[key][1])

                        # Calculate overlap of second embargo period
                        split_notice_overlap = overlap_calc(notice_period_lst[0], embargo_dct[key + 10][0], notice_period_lst[1], embargo_dct[key + 10][1])

                        # Compare overlap with gap duration
                        # Delete second embargo period total overlap fits into gap
                        if (notice_overlap + split_notice_overlap <= gap_dur) and (termination_dt < embargo_dct[key][1]):
                            del embargo_dct[key + 10]
                        else:
                            notice_overlap = notice_overlap + split_notice_overlap

                    # Keep score of embargo balance
                    embargo_balance = embargo_balance + period_duration(embargo_dct[key][0], embargo_dct[key][1])

                    # Keep score of total notice overlap
                    total_notice_overlap = total_notice_overlap + notice_overlap



    # --- CASE: MILITARY OR CIVIL SERVICE --- #

    # Selected case type
    if incapacity_type == "milservice":
        print("still to be implemented")


    # --- CASE: PREGNANCY --- #

    # Selected case type
    if incapacity_type == "preg":
        print("still to be implemented")


    # --- TERMINATION AND NOTICE PERIOD --- #

    # Check if user selected termination evaluation
    if termination_occurence == "Yes" or "Ja":

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
    else:
        new_employment_edt = termination_dt

    # Shift missed notice period days, start and end date
    # Calculated under case types
    if total_notice_overlap != 0:
        notice_period_lst.insert(2, max(notice_period_lst[1], embargo_dct[key][-1]).shift(days=+1)) # start date
        notice_period_lst.insert(3, max(notice_period_lst[1], embargo_dct[key][-1]).shift(days=+notice_overlap)) # end date
        single_date(notice_period_lst, 2, 3)

        # Create extension if needed
        if not endpoint in ["Termination date anytime", "Kündigungstermin jederzeit"]:
            extension_lst.insert(0, notice_period_lst[-1].shift(days=+1))
            extension_lst.insert(1, push_endpoint(notice_period_lst[-1], endpoint))
            single_date(extension_lst, 0, 1)
            new_employment_edt = extension_lst[-1]
        else:
            new_employment_edt = notice_period_lst[-1]


        # --- SICK PAY --- #

        # Sick pay matrix, starting after first year of service
        # Source: https://www.gerichte-zh.ch/themen/arbeit/waehrend-arbeitsverhaeltnis/arbeitsverhinderung/krankheit-und-unfall.html
        pay_matrix = [
            ["", 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42], # ZH (weeks)
            ["", 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6, 6 ,6, 6, 6 ,6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6], # BS / BL (months)
            ["", 1, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6 ,6, 6, 6 ,6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6], # BE (months)
        ]

        # Choose sick pay duration
        if workplace in ["ZH", "SH", "TG"]:
            canton = 0
            unit = "weeks"
        elif workplace in ["BS", "BL"]:
            canton = 1
            unit = "months"
        else:
            canton = 2
            unit = "months"

        # Split sick pay periods into years
        for key, value in incap_dct.items():
            for incap_sublst in value:

                sickpay_sublst_1 = incap_sublst
                sickpay_sublst_2 = []
                
                # Define sick pay start date
                sickpay_sublst_1[0] = max(employment_sdt.shift(months=3), sickpay_sublst_1[0])

                # Calculate seniority at the beginning of the incapacity
                # Source: https://stackoverflow.com/a/70038244/14819955
                sick_pay_syear_start_index = get_last_index(syears, lambda x: x < sickpay_sublst_1[0])

                # Calculate seniority at the end of the incapacity
                sick_pay_syear_end_index = get_last_index(syears, lambda x: x < sickpay_sublst_1[1])

                # Compare seniority at start and end, split if not the same
                # Group into dict according to start year
                if sick_pay_syear_start_index != sick_pay_syear_end_index: # in the same year
                    # Split period after syear
                    sickpay_sublst_2.insert(0, syears[sick_pay_syear_end_index])
                    sickpay_sublst_2.insert(1, sickpay_sublst_1[1])
                    # Cap first period a day before syear
                    sickpay_sublst_1[1] = min(sick_pay_dct[key][1], syears[sick_pay_syear_end_index].shift(days=-1))
                    # Sort second period into dict
                    sick_pay_dct[sick_pay_syear_start_index].append(sickpay_sublst_2)

                # Sort first period into dict
                sick_pay_dct[sick_pay_syear_start_index].append(sickpay_sublst_1)
                
        # Keep score of sick pay for each year
        sick_pay_balance = 0
        sick_pay_cap = 0
        
        # Loop through incapacities according to year
        for key, value in sick_pay_dct.items():
            for sickpay_sublst in value:
                while sick_pay_balance <= sick_pay_cap:

                    # Calculate sick pay according to service year
                    if sickpay_sublst[0] < syears[1]:
                        sickpay_sublst[1].shift(weeks=+3, days=-1)
                        sick_pay_cap = 21
                    else:
                        sickpay_sublst[1].shift(**{unit:(pay_matrix[canton][sick_pay_syear_start_index])}, days=-1)
                        sick_pay_cap = period_duration(sickpay_sublst[0], sickpay_sublst[1])

                    # Cap sick pay end date
                    sick_pay_dct[1] = clamp(sickpay_sublst[1], sickpay_sublst[0], min(new_employment_edt, incap_sublst[-1]))

                    sublist_sick_pay_dur = period_duration(sickpay_sublst[1], sickpay_sublst[0])

                    sick_pay_balance = sick_pay_balance + sublist_sick_pay_dur

                    # Shift back if cap is exceeded
                    if  sick_pay_balance > sick_pay_cap:
                        sick_pay_dct[1].shift(days=-sick_pay_balance-sick_pay_cap)

                    # Count sick pay duration
                    sublist_sick_pay_dur = period_duration(sickpay_sublst[1], sickpay_sublst[0])

                    # Keep score of used sick pay days
                    sick_pay_balance = sick_pay_balance + sublist_sick_pay_dur


    # --- EVALUATION --- #

    # Output
    valid_termination  = lang("✔️ Your termination appears valid.", "✔️ Ihre Kündigung scheint gültig zu sein.")
    invalid_termination = lang("❌ YOUR TERMINATION APPEARS INVALID.", "❌ IHRE KÜNDIGUNG SCHEINT UNGÜLTIG ZU SEIN.")
    no_termination = lang("No termination.", "Keine Kündigung.")

    # Standard case
    # Termination during prbation period
    if termination_occurence == "No" or "Nein":
        termination_case = "no_termination"
    elif (termination_occurence == "Yes" or "Ja") and termination_dt.is_between(trial_lst[0], trial_lst[-1], "[]"):
        termination_case = "trial_case"
    # Termination during embargo period
    elif (termination_occurence == "Yes" or "Ja"):
        for key, value in embargo_dct.items():
            for embargo_sublst in value:
                if termination_dt.is_between(embargo_sublst[0], embargo_sublst[-1], "[]"):
                    termination_case = "embargo_case"
                    break
    # Standard case
    else:
        termination_case = "standard_case"
        

    # --- Termination case: No case --- #

    if termination_case == "no_case":
        termination_validity = no_termination

    # --- Termination case: Standard case --- #

    if termination_case == "standard_case":
        termination_validity = valid_termination

    # --- Termination case: TERMINATION DURING TRIAL PERIOD --- #

    # Adjust varibles
    if termination_case == "trial_case":
        termination_validity = valid_termination
        # Set end of trial period to termination date
        trial_lst[1] = termination_dt
        # Adjust notice period
        notice_period_lst[0] = termination_dt.shift(days=+1)
        notice_period_lst[1] = termination_dt.shift(days=+7)
        total_notice_overlap = 0
        reg_employment_lst.clear()
        embargo_dct[key].clear()
        new_employment_edt = notice_period_lst[-1]


        # Cap sick at end of employment
        for key, value in sick_pay_dct.items():
            for sickpay_sublst in value:
                if sickpay_sublst[0] > new_employment_edt:
                    sickpay_sublst.clear()
                if (sickpay_sublst[0] < new_employment_edt) and sickpay_sublst[1] > new_employment_edt:
                    sickpay_sublst[1] = new_employment_edt
                
                # Recount sick pay balance
                sick_pay_balance = sick_pay_balance + period_duration(sickpay_sublst[0], sickpay_sublst[1])


    # --- Termination case: TERMINATION DURING EMBARGO PERIOD --- #

    # Adjust varibles
    if termination_case == "embargo_case":
        termination_validity = invalid_termination
        notice_period_lst.clear()
        total_notice_overlap = 0
        reg_employment_lst[1] = reg_employment_lst[1].shift(years=+5) # showing that employment continues
        extension_lst.clear()
        new_employment_edt = ""


    # --- DATE CONVERSION AND OUTPUT PREPARATION --- #


    # Convert dates from arrow to datetime for compatibility
    # Convert standalone lists
    master_lst = [trial_lst, reg_employment_lst, notice_period_lst, extension_lst]
    for lst in master_lst:
        for index, value in enumerate(lst):
            if isinstance(value, arrow.Arrow):
                lst[index] = value.datetime.date()

    # Convert lists in dicts
    for value in (incap_dct.values(), embargo_dct.values(), sick_pay_dct.values()):
        for lst in value:
            for index, value in enumerate(lst):
                if isinstance(value, arrow.Arrow):
                    lst[index] = value.datetime.date()

    # Copy local variables and covert to datetime
    local_vars = locals()
    output_dct = local_vars.copy()
    for key, value in list(output_dct.items()):
        if isinstance(value, arrow.Arrow):
            output_dct[key] = value.datetime.date()


    # --- VISUALIZATION - DATA INPUT --- #

    df = pd.DataFrame([])

    # Insert sick pay dict into dataframe
    for key, value in sick_pay_dct.items():
        for sickpay_sublst in value:
            df.append(task=lang("Sick Pay", "Lohnfortzahlung"), start=sickpay_sublst[0], end=sickpay_sublst[1], stack="stack_2", color="#f032e6")

    # Insert trial period into dataframe
    df.append(Task=lang("Probation Period", "Probezeit"), Start=check_index(trial_lst, 0), End=check_index(trial_lst, 1), Stack="f58231")

    # Insert regular employment into dataframe
    df.append(task=lang("Regular Employment", "Reguläre Anstellung"), Start=check_index(reg_employment_lst, 0), End=check_index(reg_employment_lst, 1), Stack="stack_3", color="#3cb44b")

    # Insert embargo period dict into dataframe
    for key, value in embargo_dct.items():
        for embargo_sublst in value:
            df.append(task=lang("Embargo Period", "Embargo"), Start=embargo_sublst[0], End=embargo_sublst[1], Stack="stack_3")

    # Insert regular notice period into dataframe
    df.append(task=lang("Regular Notice Period", "Ordentliche Kündigungsfrist"), Start=check_index(notice_period_lst, 0), End=check_index(notice_period_lst, 1), Stack="stack_3", color="#000075")

    # Insert missed notice period compensation into dataframe
    df.append(Task=lang("Compensation Missed Notice Period", "Kompensation verpasste Kündigungsfrist"), Start=check_index(notice_period_lst, 2), End=check_index(notice_period_lst, 3), Stack="stack_3", color="#4363d8"),

    # Insert notice period extension into dataframe
    df.append(Task=lang("Notice Period Extension", "Verlängerung Kündigungsfrist"), Start=check_index(extension_lst, 0), End=check_index(extension_lst, 1), Stack="stack_3", color="#911eb4"),

    # Insert incapacity dict into dataframe
    for key, value in incap_dct.items():
        for incap_sublst in value:
            df.append(task=lang("Incapacity", "Krankheit"), Start=incap_sublst[0], End=incap_sublst[1], Stack="stack_3", color="#800000")

    # Insert place holders into dataframe
    df.insert(0, task="[PH_T]", start=output_dct["termination_dt"], end=output_dct["termination_dt"], stack="stack_1", color="#ffffff")
    df.append(-1, task="[PH_B]", start=output_dct["termination_dt"], end=output_dct["termination_dt"], stack="stack_5", color="#ffffff")

    # --- VISUALIZATION - FORMAT --- #

    fig = px.timeline(df,
                x_start="Start",
                x_end="End",
                y="Stack",
                opacity=1,
                color="Task",
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

    fig.update_xaxes(range=[output_dct["employment_sdt"], incap_dct[key][1]])

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

    # Reformat dates to omit time info
    # Output dict
    for key, value in list(output_dct.items()):
        if isinstance(value, datetime.date):
            output_dct[key] = value.strftime("%d.%m.%Y")

    # Standalone lists
    for lst in master_lst:
        for index, value in enumerate(lst):
            if isinstance(value, datetime.date):
                lst[index] = value.strftime("%d.%m.%Y")

    # Dicts
    for value in (incap_dct.values(), embargo_dct.values(), sick_pay_dct.values()):
        for sublst in value:
            for index, subvalue in enumerate(sublst):
                if isinstance(subvalue, datetime.date):
                    sublst[index] = subvalue.strftime("%d.%m.%Y")

    # Increase max width for visualization
    session.set_env(output_max_width="1080px")

    with output.use_scope("scope1", clear=True):
        output.put_markdown("""## Input"""), None,
        output.put_table([
        [lang("Event", "Ereignis"), lang("Date", "Datum")],
        [lang("Employment Start Date", "Beginn Arbeitsverhältnis"), output_dct["employment_sdt"]],
        [lang("Date of Termination", "Kündigungsdatum"), output_dct["termination_dt"]],
        [lang("Incapacity Start Date", "Beginn Arbeitsunfähigkeit"), incap_output_sdt],
        [lang("Incapacity End Date", "Ende Arbeitsunfähigkeit"), incap_output_edt],
        ])

        for key, value in incap_dct.items():
            for incap_sublst in value:
                incap_output_sdt = incap_output_sdt.append(incap_sublst[0])
                incap_output_edt = incap_output_edt.append(incap_sublst[1])

        output.put_markdown(lang("""## Non-binding Evaluation""", """## Unverbindliche Auswertung""")).style('margin-top: 20px'), None,
        output.put_markdown(lang("""### Embargo and Notice Periods""", """### Kündigungs- und Sperrfristen """)).style('margin-top: 20px'), None,
        output.put_table([
        [lang("Query", "Abfrage"), lang("Result", "Ergebnis")],
        [lang("Validity of Termination:", "Gültigkeit der Kündigung:"), output_dct["termination_validity"]],
        [lang("Original end date of employment:", "Ursprüngliches Enddatum der Anstellung:"), notice_period_lst[1]],
        [lang("Missed Working Days Probation Period:", "Verpasste Arbeitstage Probezeit:"), str(len(missed_workdays)) + lang(" days", " Tage")],
        [lang("Missed Calendar Days Notice Period:", "Verpasste Kalendertage Kündigungsfrist:"), str(total_notice_overlap) + lang(" days", " Tage")],
        [lang("Total Embargo Duration:", "Gesamtdauer Sperrfrist:"), str("") + lang(" days", " Tage")],
        [lang("New End Date of Employment:", "Neues Enddatum der Anstellung:"), output_dct["new_employment_edt"]],
        ])

        output.put_markdown(lang("""### Sick Pay""", """### Lohnfortzahlung """)).style('margin-top: 20px'), None,
        output.put_table([
        ["", lang("Start Date", "Anfangsdatum"), lang("End Date", "Enddatum"), lang("Duration", "Dauer")],
        [lang("1. Period:", "1. Periode:"), incap_output_sdt, incap_output_edt, sick_pay_period_dur + lang(" days", " Tage")],
        ["Total:", "", "", str(sick_pay_balance) + lang(" days", " Tage")]
        ])

        for key, value in sick_pay_dct:
            for sick_pay_sublst in value:
                incap_output_sdt = incap_output_sdt.append(sick_pay_sublst[0])
                incap_output_edt = incap_output_edt.append(sick_pay_sublst[1])
                sick_pay_period_dur = str(period_duration(sick_pay_sublst[0], sick_pay_sublst[1]))

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
