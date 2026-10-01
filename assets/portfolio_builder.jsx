/* InDesign ExtendScript. PORTFOLIO_SPEC and PORTFOLIO_FORCE are injected by portfolio_cli.py. */
(function () {
    var spec = PORTFOLIO_SPEC;
    var doc = null;
    var warnings = [];
    var overset = [];
    var frames = [];
    var pageCount = 0;

    function quote(value) {
        return '"' + String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"')
            .replace(/\r/g, '\\r').replace(/\n/g, '\\n').replace(/\t/g, '\\t') + '"';
    }
    function jsonArray(items) {
        var parts = [];
        for (var i = 0; i < items.length; i++) parts.push(quote(items[i]));
        return '[' + parts.join(',') + ']';
    }
    function writeReport(ok, error) {
        var path = spec.output.report;
        var file = new File(path);
        file.encoding = 'UTF-8';
        if (!file.open('w')) return;
        file.write('{"ok":' + (ok ? 'true' : 'false') + ',"error":' + quote(error || '') +
            ',"pages":' + pageCount + ',"warnings":' + jsonArray(warnings) +
            ',"overset_pages":' + jsonArray(overset) + ',"indd":' + quote(spec.output.indd) +
            ',"pdf":' + quote(spec.output.pdf) + '}');
        file.close();
    }
    function rgb(hex) {
        return [parseInt(hex.substr(1, 2), 16), parseInt(hex.substr(3, 2), 16), parseInt(hex.substr(5, 2), 16)];
    }
    function swatch(name, hex) {
        var c = doc.colors.itemByName(name);
        if (!c.isValid) c = doc.colors.add({name: name, model: ColorModel.PROCESS, space: ColorSpace.RGB, colorValue: rgb(hex)});
        return c;
    }
    function box(page, x, y, w, h, color) {
        var item = page.rectangles.add();
        item.geometricBounds = [y, x, y + h, x + w];
        item.fillColor = color;
        item.strokeWeight = 0;
        return item;
    }
    function text(page, value, x, y, w, h, size, color, weight, label) {
        if (!value) return null;
        var frame = page.textFrames.add();
        frame.geometricBounds = [y, x, y + h, x + w];
        frame.textFramePreferences.insetSpacing = [0, 0, 0, 0];
        frame.contents = String(value || '');
        frame.label = label || '';
        var contents = frame.texts.item(0);
        contents.pointSize = size;
        contents.leading = size * 1.22;
        contents.fillColor = color;
        var fontName = weight === 'bold' ? spec.theme.bold : spec.theme.regular;
        try { contents.appliedFont = fontName; }
        catch (fontError) { warnings.push('Font unavailable: ' + fontName + ' (' + frame.label + ')'); }
        frames.push({frame: frame, page: page.name, label: frame.label});
        return frame;
    }
    function image(page, path, x, y, w, h, label) {
        if (!path) return false;
        var file = new File(path);
        if (!file.exists) { warnings.push('Image unavailable: ' + path); return false; }
        var frame = page.rectangles.add();
        frame.geometricBounds = [y, x, y + h, x + w];
        frame.strokeWeight = 0;
        frame.label = label || '';
        try {
            frame.place(file);
            frame.fit(FitOptions.FILL_PROPORTIONALLY);
            return true;
        } catch (placeError) {
            warnings.push('Could not place ' + path + ': ' + String(placeError));
            frame.remove();
            return false;
        }
    }
    function newPage() {
        var page = pageCount === 0 ? doc.pages.item(0) : doc.pages.add(LocationOptions.AT_END);
        pageCount++;
        box(page, 0, 0, spec.page.width_pt, spec.page.height_pt, background);
        return page;
    }

    var background, ink, accent, muted;
    try {
        if (!PORTFOLIO_FORCE && (new File(spec.output.indd).exists || new File(spec.output.pdf).exists))
            throw Error('Output already exists. Change output paths or run with --force.');
        doc = app.documents.add();
        doc.documentPreferences.pageWidth = spec.page.width_pt + 'pt';
        doc.documentPreferences.pageHeight = spec.page.height_pt + 'pt';
        doc.documentPreferences.facingPages = false;
        background = swatch('Portfolio Background', spec.theme.background);
        ink = swatch('Portfolio Text', spec.theme.text);
        accent = swatch('Portfolio Accent', spec.theme.accent);
        muted = swatch('Portfolio Muted', spec.theme.muted);

        var W = spec.page.width_pt, H = spec.page.height_pt, M = spec.page.margin_pt;
        var inner = W - 2 * M;
        var p = newPage();
        var heroH = H * 0.57;
        if (!image(p, spec.profile.hero_image, 0, 0, W, heroH, 'cover-hero'))
            box(p, M, M, inner, heroH - M, accent);
        text(p, spec.title.toUpperCase(), M, heroH + 24, inner, 34, 14, accent, 'bold', 'cover-kicker');
        text(p, spec.profile.name, M, heroH + 68, inner, 76, 43, ink, 'bold', 'cover-name');
        text(p, spec.profile.headline, M, heroH + 153, inner, 92, 18, muted, 'regular', 'cover-headline');

        p = newPage();
        text(p, 'ABOUT', M, M, inner, 32, 13, accent, 'bold', 'about-kicker');
        text(p, spec.profile.name, M, M + 45, inner, 64, 34, ink, 'bold', 'about-name');
        text(p, spec.profile.bio, M, M + 123, inner, H * 0.30, 16, ink, 'regular', 'about-bio');
        var contactY = H * 0.54;
        text(p, spec.profile.contact.join('\r'), M, contactY, inner, 70, 12, muted, 'regular', 'about-contact');
        text(p, 'SELECTED WORK', M, H * 0.69, inner, 28, 13, accent, 'bold', 'index-kicker');
        var indexLines = [];
        for (var i = 0; i < spec.projects.length; i++)
            indexLines.push(('0' + (i + 1)).slice(-2) + '  ' + spec.projects[i].title);
        text(p, indexLines.join('\r'), M, H * 0.74, inner, H * 0.20, 17, ink, 'regular', 'project-index');

        for (var j = 0; j < spec.projects.length; j++) {
            var project = spec.projects[j];
            p = newPage();
            text(p, 'PROJECT ' + ('0' + (j + 1)).slice(-2), M, M, inner, 30, 12, accent, 'bold', 'project-number');
            text(p, project.title, M, M + 39, inner, 73, 34, ink, 'bold', 'project-title');
            text(p, project.subtitle, M, M + 111, inner, 50, 16, muted, 'regular', 'project-subtitle');
            var imageY = M + 174, imageH = H * 0.39;
            if (!image(p, project.hero_image, M, imageY, inner, imageH, 'project-hero-' + j))
                box(p, M, imageY, inner, imageH, accent);
            var metaY = imageY + imageH + 19;
            text(p, [project.role, project.year].join('  |  '), M, metaY, inner, 30, 11, accent, 'bold', 'project-meta');
            text(p, project.summary, M, metaY + 35, inner, H - (metaY + 35) - M, 14, ink, 'regular', 'project-summary');

            if (project.images.length || project.facts.length) {
                p = newPage();
                text(p, project.title.toUpperCase(), M, M, inner, 35, 14, accent, 'bold', 'detail-title');
                var galleryY = M + 52, galleryH = H * 0.43;
                if (project.images.length === 1) {
                    image(p, project.images[0], M, galleryY, inner, galleryH, 'gallery-1');
                } else if (project.images.length === 2) {
                    var gap = 12, half = (inner - gap) / 2;
                    image(p, project.images[0], M, galleryY, half, galleryH, 'gallery-1');
                    image(p, project.images[1], M + half + gap, galleryY, half, galleryH, 'gallery-2');
                } else {
                    box(p, M, galleryY, inner, galleryH, accent);
                    text(p, project.facts[0], M + 25, galleryY + 35, inner - 50,
                        galleryH - 70, 25, background, 'bold', 'feature-fact');
                }
                text(p, 'RESULTS & DETAILS', M, galleryY + galleryH + 30, inner, 30, 13, accent, 'bold', 'facts-kicker');
                text(p, (project.images.length ? project.facts : project.facts.slice(1)).join('\r'), M, galleryY + galleryH + 72,
                    inner, H - (galleryY + galleryH + 72) - M, 15, ink, 'regular', 'project-facts');
            }
        }

        for (var k = 0; k < frames.length; k++) {
            if (frames[k].frame.overflows)
                overset.push('Page ' + frames[k].page + ': ' + frames[k].label);
        }
        if (overset.length) warnings.push('Overset text found; revise copy or layout before delivery.');

        doc.save(new File(spec.output.indd));
        doc.exportFile(ExportFormat.PDF_TYPE, new File(spec.output.pdf), false);
        writeReport(warnings.length === 0, '');
    } catch (error) {
        writeReport(false, String(error));
        throw error;
    }
})();
