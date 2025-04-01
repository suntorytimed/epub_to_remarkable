const translations = {
    de: {
        title: "eBook to PDF Converter",
        disclaimerTitle: "Rechtliche Hinweise",
        dataStorageTitle: "Datenspeicherung",
        dataStorageText: "Alle hochgeladenen Dateien werden nur temporär für den Konvertierungsprozess gespeichert. Nach erfolgreicher Konvertierung bleiben die Dateien für einen begrenzten Zeitraum (maximal {{ timeout_minutes }} Minuten) verfügbar, um den Download zu ermöglichen. Danach werden sie automatisch gelöscht. Wir speichern keine Benutzer- oder Dateimetadaten über diesen Zeitraum hinaus.",
        contentResponsibilityTitle: "Inhaltsverantwortung",
        contentResponsibilityText: "Benutzer sind allein verantwortlich für die Inhalte der hochgeladenen Dateien. Das Hochladen oder Konvertieren von urheberrechtlich geschütztem Material ohne entsprechende Rechte, sowie von illegalen, beleidigenden oder anderweitig rechtswidrigen Inhalten ist strengstens untersagt. Der Betreiber dieses Dienstes behält sich das Recht vor, verdächtige Aktivitäten zu untersuchen und bei Bedarf an die zuständigen Behörden zu melden.",
        liabilityTitle: "Haftungsausschluss",
        liabilityText: "Dieser Dienst wird \"wie er ist\" und ohne jegliche Garantie bereitgestellt. Der Betreiber übernimmt keine Haftung für Schäden, die durch die Nutzung dieses Dienstes entstehen könnten, einschließlich, aber nicht beschränkt auf Datenverlust, Systemschäden oder andere technische Probleme. Die Nutzung erfolgt auf eigenes Risiko. Der Betreiber garantiert nicht die ununterbrochene oder fehlerfreie Verfügbarkeit des Dienstes.",
        copyrightTitle: "Urheberrecht",
        copyrightText: "Benutzer dürfen diesen Dienst nur zur Konvertierung von Dateien verwenden, an denen sie die entsprechenden Rechte besitzen. Dies umfasst persönliche Dokumente, Werke unter freien Lizenzen oder Material, für das Sie die ausdrückliche Erlaubnis zur Konvertierung haben. Die Konvertierung urheberrechtlich geschützter Werke ohne entsprechende Genehmigung ist verboten und kann rechtliche Konsequenzen nach sich ziehen.",
        termsOfUseTitle: "Nutzungsbedingungen",
        termsOfUseText: "Durch die Nutzung dieses Dienstes erklären Sie sich mit diesen Bedingungen einverstanden. Bei Verstößen gegen diese Bedingungen kann Ihnen die Nutzung des Dienstes untersagt werden. Sie stimmen zu, den Dienst nicht zu missbrauchen, keine automatisierten Massenanfragen zu stellen und keine Maßnahmen zu ergreifen, die die Funktionsfähigkeit des Dienstes beeinträchtigen könnten.",
        backToConverter: "Zurück zum Konverter",
        deviceSelection: "Geräteauswahl",
        selectDeviceProfile: "Wähle Geräteprofil:",
        remarkablePro: "reMarkable Paper Pro",
        booxAir4c: "Boox Air 4c",
        userDefined: "Benutzerdefiniert",
        uploadFile: "Datei hochladen",
        selectEpubFile: "EPUB-Datei auswählen:",
        conversionParameters: "Konvertierungsparameter",
        inputProfile: "Eingabeprofil:",
        outputProfile: "Ausgabeprofil:",
        fontSizes: "Schriftgrößen",
        baseFontSize: "Basis-Schriftgröße:",
        defaultFontSize: "Standard-Schriftgröße:",
        monoFontSize: "Monospace-Schriftgröße:",
        fontOptions: "Schriftoptionen",
        embedAllFonts: "Alle Schriften einbetten",
        subsetEmbeddedFonts: "Eingebettete Schriften beschränken",
        unsmartenPunctuation: "Anführungszeichen vereinfachen",
        sizeLayout: "Größe & Layout",
        customSize: "Benutzerdefinierte Größe:",
        unit: "Einheit:",
        pdfFonts: "PDF-Schriften",
        pdfSansFamily: "PDF Sans-Schriftfamilie:",
        pdfSerifFamily: "PDF Serif-Schriftfamilie:",
        pdfMonoFamily: "PDF Monospace-Schriftfamilie:",
        pdfStandardFont: "PDF Standardschrift:",
        pdfMargins: "PDF-Ränder",
        leftMargin: "Linker Rand:",
        rightMargin: "Rechter Rand:",
        topMargin: "Oberer Rand:",
        bottomMargin: "Unterer Rand:",
        otherSettings: "Weitere Einstellungen",
        preserveCoverAspectRatio: "Seitenverhältnis des Covers beibehalten",
        justification: "Ausrichtung:",
        convertToPDF: "Zu PDF konvertieren",
        selectFile: "Durchsuchen...",
        noFileSelected: "Keine Datei ausgewählt",
        byUsingService: "Durch die Nutzung dieses Dienstes akzeptieren Sie unsere",
        legalTerms: "rechtlichen Hinweise",
        status: "Status",
        statusRunning: "Konvertierung läuft...",
        statusCompleted: "Abgeschlossen",
        statusFailed: "Fehlgeschlagen",
        statusLostConnection: "Verbindung verloren",
        statusSearching: "Suche nach PDF...",
        statusInProgress: "In Bearbeitung",
        tooltip: "Wenn der Status nicht korrekt angezeigt wird, kann es sein, dass die Konvertierung trotzdem im Hintergrund läuft. Bitte warten Sie einige Minuten und klicken Sie dann auf \"Verbindung wiederherstellen\".",
        startingConversion: "Starte Konvertierung...",
        conversionDetails: "Konvertierungsdetails",
        errorMessage: "Fehlermeldung",
        downloadPDF: "PDF herunterladen",
        backToForm: "Zurück zum Formular",
        reconnect: "Verbindung wiederherstellen",
        reconnecting: "Verbindung wird wiederhergestellt...",
        conversionSuccessful: "Konvertierung erfolgreich abgeschlossen!",
        conversionInProgress: "Die Konvertierung scheint noch im Gange zu sein oder ist fehlgeschlagen. Bitte versuchen Sie es später erneut.",
        errorOccurred: "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut.",
        connectionLost: "Die Server-Verbindung wurde unterbrochen. Die Konvertierung läuft aber möglicherweise noch im Hintergrund. Bitte verwenden Sie den \"Verbindung wiederherstellen\"-Button, um die Verbindung erneut herzustellen.",
        attention: "Achtung",
        statusInconsistency: "Die Statusanzeige ist widersprüchlich. Bitte klicken Sie auf \"Verbindung wiederherstellen\", um den tatsächlichen Status zu prüfen.",
        jobNotFoundError: "Der Konvertierungsauftrag wurde nicht gefunden. Dies kann passieren, wenn:\n- Die Seite neu geladen wurde\n- Der Server neu gestartet wurde\n- Der Auftrag bereits abgeschlossen oder abgelaufen ist\n\nBitte versuchen Sie es erneut mit einer neuen Konvertierung.",
        systemDiagnosis: "System-Diagnose",
        systemStatus: "Systemstatus",
        calibre: "Calibre:",
        ibmPlexFonts: "IBM Plex Schriftarten:",
        installed: "Installiert",
        notFound: "Nicht gefunden",
        tempDirectory: "Temporäres Verzeichnis:",
        writable: "Schreibbar",
        notWritable: "Nicht schreibbar",
        pythonVersion: "Python Version:",
        activeJobs: "Aktive Jobs:",
        completedFiles: "Abgeschlossene Dateien:",
        availableFonts: "Verfügbare Schriftarten",
        errorRetrievingFonts: "Fehler beim Abrufen der Schriftarten:",
        noFontsFound: "Keine Schriftarten gefunden",
        diskSpace: "Speicherplatz",
        environmentVariables: "Umgebungsvariablen",
        backToHomepage: "Zurück zur Startseite"
    },
    en: {
        title: "eBook to PDF Converter",
        disclaimerTitle: "Legal Disclaimer",
        dataStorageTitle: "Data Storage",
        dataStorageText: "All uploaded files are stored temporarily for the conversion process only. After successful conversion, files remain available for a limited period (maximum {{ timeout_minutes }} minutes) to allow downloading. They are then automatically deleted. We do not store any user or file metadata beyond this period.",
        contentResponsibilityTitle: "Content Responsibility",
        contentResponsibilityText: "Users are solely responsible for the content of uploaded files. Uploading or converting copyrighted material without appropriate rights, as well as illegal, offensive, or otherwise unlawful content is strictly prohibited. The operator of this service reserves the right to investigate suspicious activities and report them to the appropriate authorities if necessary.",
        liabilityTitle: "Disclaimer of Liability",
        liabilityText: "This service is provided \"as is\" and without any warranty. The operator assumes no liability for damages that may arise from the use of this service, including but not limited to data loss, system damage, or other technical issues. Use is at your own risk. The operator does not guarantee uninterrupted or error-free availability of the service.",
        copyrightTitle: "Copyright",
        copyrightText: "Users may only use this service to convert files for which they have the appropriate rights. This includes personal documents, works under free licenses, or material for which you have explicit permission to convert. Converting copyrighted works without appropriate permission is prohibited and may have legal consequences.",
        termsOfUseTitle: "Terms of Use",
        termsOfUseText: "By using this service, you agree to these terms. Violations of these terms may result in your being prohibited from using the service. You agree not to abuse the service, not to make automated mass requests, and not to take any actions that could impair the functionality of the service.",
        backToConverter: "Back to Converter",
        deviceSelection: "Device Selection",
        selectDeviceProfile: "Select Device Profile:",
        remarkablePro: "reMarkable Paper Pro",
        booxAir4c: "Boox Air 4c",
        userDefined: "User Defined",
        uploadFile: "Upload File",
        selectEpubFile: "Select EPUB File:",
        conversionParameters: "Conversion Parameters",
        inputProfile: "Input Profile:",
        outputProfile: "Output Profile:",
        fontSizes: "Font Sizes",
        baseFontSize: "Base Font Size:",
        defaultFontSize: "Default Font Size:",
        monoFontSize: "Monospace Font Size:",
        fontOptions: "Font Options",
        embedAllFonts: "Embed All Fonts",
        subsetEmbeddedFonts: "Subset Embedded Fonts",
        unsmartenPunctuation: "Simplify Punctuation",
        sizeLayout: "Size & Layout",
        customSize: "Custom Size:",
        unit: "Unit:",
        pdfFonts: "PDF Fonts",
        pdfSansFamily: "PDF Sans Family:",
        pdfSerifFamily: "PDF Serif Family:",
        pdfMonoFamily: "PDF Monospace Family:",
        pdfStandardFont: "PDF Standard Font:",
        pdfMargins: "PDF Margins",
        leftMargin: "Left Margin:",
        rightMargin: "Right Margin:",
        topMargin: "Top Margin:",
        bottomMargin: "Bottom Margin:",
        otherSettings: "Other Settings",
        preserveCoverAspectRatio: "Preserve Cover Aspect Ratio",
        justification: "Justification:",
        convertToPDF: "Convert to PDF",
        selectFile: "Browse...",
        noFileSelected: "No file selected",
        byUsingService: "By using this service, you accept our",
        legalTerms: "legal terms",
        status: "Status",
        statusRunning: "Conversion in progress...",
        statusCompleted: "Completed",
        statusFailed: "Failed",
        statusLostConnection: "Connection lost",
        statusSearching: "Searching for PDF...",
        statusInProgress: "In progress",
        tooltip: "If the status is not displayed correctly, the conversion may still be running in the background. Please wait a few minutes and then click \"Reconnect\".",
        startingConversion: "Starting conversion...",
        conversionDetails: "Conversion Details",
        errorMessage: "Error Message",
        downloadPDF: "Download PDF",
        backToForm: "Back to Form",
        reconnect: "Reconnect",
        reconnecting: "Reconnecting...",
        conversionSuccessful: "Conversion completed successfully!",
        conversionInProgress: "The conversion appears to be still in progress or has failed. Please try again later.",
        errorOccurred: "An error occurred. Please try again later.",
        connectionLost: "The server connection was interrupted. The conversion may still be running in the background. Please use the \"Reconnect\" button to re-establish the connection.",
        attention: "Attention",
        statusInconsistency: "The status display is inconsistent. Please click on \"Reconnect\" to check the actual status.",
        jobNotFoundError: "The conversion job was not found. This can happen if:\n- The page was reloaded\n- The server was restarted\n- The job has already completed or expired\n\nPlease try again with a new conversion.",
        systemDiagnosis: "System Diagnosis",
        systemStatus: "System Status",
        calibre: "Calibre:",
        ibmPlexFonts: "IBM Plex Fonts:",
        installed: "Installed",
        notFound: "Not found",
        tempDirectory: "Temporary Directory:",
        writable: "Writable",
        notWritable: "Not writable",
        pythonVersion: "Python Version:",
        activeJobs: "Active Jobs:",
        completedFiles: "Completed Files:",
        availableFonts: "Available Fonts",
        errorRetrievingFonts: "Error retrieving fonts:",
        noFontsFound: "No fonts found",
        diskSpace: "Disk Space",
        environmentVariables: "Environment Variables",
        backToHomepage: "Back to Homepage"
    }
};

const availableLanguages = {
    'de': 'Deutsch',
    'en': 'English'
};

const i18n = {
    getCurrentLanguage: function() {
        return localStorage.getItem('preferredLanguage') || 'de';
    },
    
    setLanguage: function(lang) {
        if (translations[lang]) {
            localStorage.setItem('preferredLanguage', lang);
            document.documentElement.lang = lang;
            this.updatePageContent();
            return true;
        }
        return false;
    },
    
    translate: function(key) {
        const lang = this.getCurrentLanguage();
        return translations[lang] && translations[lang][key] ? 
               translations[lang][key] : key;
    },

    replacePlaceholders: function(text) {
        if (typeof window.timeoutMinutes !== 'undefined') {
            text = text.replace(/\{\{\s*timeout_minutes\s*\}\}/g, window.timeoutMinutes);
        }

        return text;
    },
    
    updatePageContent: function() {
        const lang = this.getCurrentLanguage();
        
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (translations[lang] && translations[lang][key]) {
		        let text = translations[lang][key];

                text = this.replacePlaceholders(text);
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    if (element.type !== 'checkbox' && element.type !== 'radio') {
                        element.placeholder = text;
                    }
                } else if (element.tagName === 'OPTION') {
                    element.text = text;
                } else {
                    element.textContent = text;
                }
            }
        });
        
        document.querySelectorAll('p[data-i18n="byUsingService"]').forEach(paragraph => {
            const paragraphText = translations[lang]["byUsingService"];
            const linkText = translations[lang]["legalTerms"];
            
            paragraph.innerHTML = paragraphText + ' <a href="/disclaimer">' + 
                                 linkText + '</a>.';
        });
        
        this.updateLanguageSelector();
    },
    
    updateLanguageSelector: function() {
        const container = document.querySelector('.language-switcher');
        if (!container) return;
        
        container.innerHTML = '';
        
        const select = document.createElement('select');
        select.className = 'language-select';
        
        Object.keys(availableLanguages).forEach(langCode => {
            const option = document.createElement('option');
            option.value = langCode;
            option.textContent = availableLanguages[langCode];
            if (langCode === this.getCurrentLanguage()) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        select.addEventListener('change', function() {
            i18n.setLanguage(this.value);
        });
        
        container.appendChild(select);
    }
};

document.addEventListener('DOMContentLoaded', function() {
    i18n.updatePageContent();
});