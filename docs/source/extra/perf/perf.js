/*
 * The chart page of the nightly performance job.  Plain JavaScript, no
 * library.  The page reads points.json of the history branch (see
 * tests/lib/benchmarks/history.py) and draws one figure per suite, made of
 * small panels, one per item: a line of the chosen metric over time, the
 * last value at its end, a hollow marker where the rewrite steps changed, a
 * cross on the baseline where a run failed, a crosshair with a readout on
 * hover and on the arrow keys, and a table view of the last run of every
 * item against the previous one.  The functions that build the markup are
 * pure and exported, so a test runs them under node.
 */
(function (root) {
'use strict';

var BRANCH = 'perf-history';
var SUITES = ['throughput', 'compile', 'import', 'memory', 'split'];
var METRICS = {
    cpu: {label: 'CPU seconds', unit: 's'}
  , wall: {label: 'wall seconds', unit: 's'}
  , eval_wall: {label: 'evaluation seconds', unit: 's'}
  , compile: {label: 'compile seconds', unit: 's'}
  , peak_rss: {label: 'peak RSS', unit: 'MB', scale: 1 / 1048576}
  , steps: {label: 'rewrite steps', unit: ''}
  };
// The metric of a suite when the page says "suite default".
var DEFAULT_METRIC = {memory: 'peak_rss'};
// The ranges of the page in days; 0 is the whole history.
var RANGES = {all: 0, year: 365, quarter: 90, month: 30};
// The noise band of the compare command.
var THRESHOLD = 0.10;
var DAY = 86400000;
var DESCRIPTIONS = {
    throughput: 'sprite-exec -t --stats -m PROGRAM in a new process; the '
              + 'median of the repetitions.'
  , compile: 'The program compiled from source with the ICurry cache cold '
           + 'or warm; the expression item compiles 1+2 from Python.'
  , import: 'The start of the interpreter, import curry, the import of the '
          + 'Prelude, and Hello end to end.'
  , memory: 'The throughput command with the collector on and off.'
  , split: 'A search program whole and split by hand into parts.'
  };
// The geometry of a panel, in viewBox units.
var PANEL = {width: 320, height: 150, top: 14, right: 72, bottom: 24, left: 46};

function esc(text) {
  return String(text).replace(/[&<>"']/g, function (c) {
    return {
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c];
  });
}

function round(x) {
  return Math.round(x * 10) / 10;
}

/*
 * The places to look for points.json, in order: the URL of the history
 * query parameter alone when given; else the configured URL (data-history
 * of the body), the history branch of the repository when the page is
 * served from GitHub Pages, and a file beside the page.
 */
function historyUrls(location, configured) {
  var query = /[?&]history=([^&#]+)/.exec(location.search || '');
  if (query) {
    return [decodeURIComponent(query[1])];
  }
  var urls = [];
  if (configured) {
    urls.push(configured);
  }
  var host = /^([^.]+)\.github\.io$/.exec(location.hostname || '');
  var repo = /^\/([^\/]+)\//.exec(location.pathname || '');
  if (host && repo) {
    urls.push(
        'https://raw.githubusercontent.com/' + host[1] + '/' + repo[1] + '/'
      + BRANCH + '/points.json'
      );
  }
  urls.push('points.json');
  return urls;
}

function suiteOrder(suite) {
  var i = SUITES.indexOf(suite);
  return i < 0 ? SUITES.length : i;
}

function seriesKey(p) {
  return [p.suite, p.program, p.backend, p.variant || ''].join('\u0000');
}

/*
 * The series of the points: one per suite, program, backend, and variant,
 * the points in time order; the suites in their fixed order, the items in
 * the order of their first point.
 */
function groupSeries(points) {
  var map = {}, list = [];
  points.forEach(function (p) {
    var key = seriesKey(p);
    if (!map[key]) {
      map[key] = {
          key: key, suite: p.suite, program: p.program, backend: p.backend
        , variant: p.variant || null, points: []
        };
      list.push(map[key]);
    }
    map[key].points.push(p);
  });
  list.forEach(function (s) {
    s.points.sort(function (a, b) {
      return a.date < b.date ? -1 : a.date > b.date ? 1 : 0;
    });
  });
  list.sort(function (a, b) {
    return suiteOrder(a.suite) - suiteOrder(b.suite);
  });
  return list;
}

function backendsOf(seriesList) {
  var seen = [];
  seriesList.forEach(function (s) {
    if (seen.indexOf(s.backend) < 0) {
      seen.push(s.backend);
    }
  });
  return seen;
}

function titleOf(series, backends) {
  var title = series.program;
  if (series.variant) {
    title += ' (' + series.variant + ')';
  }
  if (backends > 1) {
    title += ' [' + series.backend + ']';
  }
  return title;
}

function metricOf(suite, metric) {
  if (metric && metric !== 'default' && METRICS[metric]) {
    return metric;
  }
  return DEFAULT_METRIC[suite] || 'cpu';
}

/* The value of a point in the unit of the metric; null without one. */
function valueOf(point, metric) {
  if (point.status !== 'ok' || point[metric] == null) {
    return null;
  }
  var m = METRICS[metric];
  return m.scale ? point[metric] * m.scale : point[metric];
}

function formatNumber(v, metric) {
  if (v == null) {
    return '-';
  }
  if (metric === 'steps' || metric === 'forks') {
    return Math.round(v).toLocaleString('en-US');
  }
  if (metric === 'peak_rss' && v >= 100) {
    return Math.round(v).toLocaleString('en-US');
  }
  return String(+v.toPrecision(3));
}

function formatValue(v, metric) {
  if (v == null) {
    return '-';
  }
  var unit = METRICS[metric].unit;
  return formatNumber(v, metric) + (unit ? ' ' + unit : '');
}

function formatDate(iso) {
  return String(iso).slice(0, 10);
}

function timeOf(point) {
  return Date.parse(point.date);
}

function since(range, now) {
  var days = RANGES[range] || 0;
  return days ? now - days * DAY : -Infinity;
}

function visiblePoints(series, range, now) {
  var t0 = since(range, now);
  return series.points.filter(function (p) {
    return timeOf(p) >= t0;
  });
}

/*
 * The time domain of a figure: the first and the last visible point of
 * its series, padded when they fall on one instant; null without points.
 */
function domainOf(seriesList, range, now) {
  var t0 = Infinity, t1 = -Infinity, first = null, last = null;
  seriesList.forEach(function (s) {
    visiblePoints(s, range, now).forEach(function (p) {
      var t = timeOf(p);
      if (t < t0) {
        t0 = t;
        first = p.date;
      }
      if (t > t1) {
        t1 = t;
        last = p.date;
      }
    });
  });
  if (t0 === Infinity) {
    return null;
  }
  if (t1 - t0 < DAY) {
    t0 -= DAY / 2;
    t1 += DAY / 2;
  }
  return {t0: t0, t1: t1, first: first, last: last};
}

/* The smallest clean number at or above max; 1 for nothing. */
function niceCeiling(max) {
  if (!(max > 0)) {
    return 1;
  }
  var magnitude = Math.pow(10, Math.floor(Math.log10(max)));
  var steps = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
  for (var i = 0; i < steps.length; i++) {
    if (steps[i] * magnitude >= max) {
      return steps[i] * magnitude;
    }
  }
  return 10 * magnitude;
}

/*
 * The marks of a panel: the visible points placed in the plot area, with
 * the value, and whether the rewrite steps changed from the previous
 * successful run.
 */
function layoutPanel(series, metric, dom, range, now) {
  var pts = visiblePoints(series, range, now);
  var plot = {
      x0: PANEL.left, x1: PANEL.width - PANEL.right, y0: PANEL.top
    , y1: PANEL.height - PANEL.bottom
    };
  var values = pts.map(function (p) { return valueOf(p, metric); });
  var max = 0;
  values.forEach(function (v) {
    if (v != null && v > max) {
      max = v;
    }
  });
  var ymax = niceCeiling(max);
  var span = dom ? (dom.t1 - dom.t0) || 1 : 1;
  var previous = null;
  var marks = pts.map(function (p, i) {
    var v = values[i];
    var x = dom
        ? plot.x0 + (timeOf(p) - dom.t0) / span * (plot.x1 - plot.x0)
        : plot.x0;
    var y = v == null ? plot.y1 : plot.y1 - v / ymax * (plot.y1 - plot.y0);
    var changed = v != null && previous != null && p.steps != null
               && p.steps !== previous;
    var mark = {
        point: p, value: v, x: round(x), y: round(y), changed: changed
      , previousSteps: previous
      };
    if (p.status === 'ok' && p.steps != null) {
      previous = p.steps;
    }
    return mark;
  });
  return {plot: plot, ymax: ymax, marks: marks};
}

/*
 * The last run of a series, the last successful run before it, and the
 * ratio of their values; the last run counts even when it failed.
 */
function latestOf(series, metric) {
  var pts = series.points, latest = null, previous = null;
  for (var i = pts.length - 1; i >= 0; i--) {
    var v = valueOf(pts[i], metric);
    if (latest === null) {
      latest = {point: pts[i], value: v};
    } else if (v != null) {
      previous = {point: pts[i], value: v};
      break;
    }
  }
  var ratio = null;
  if (latest && latest.value != null && previous && previous.value) {
    ratio = latest.value / previous.value;
  }
  return {latest: latest, previous: previous, ratio: ratio};
}

function verdictOf(ratio) {
  if (ratio > 1 + THRESHOLD) {
    return 'slower';
  }
  if (ratio < 1 - THRESHOLD) {
    return 'faster';
  }
  return 'same';
}

function stepsChanged(summary) {
  var a = summary.latest, b = summary.previous;
  return !!(a && b && a.point.steps != null && b.point.steps != null
            && a.point.steps !== b.point.steps);
}

function panelSvg(series, metric, dom, range, now, id, title) {
  var lay = layoutPanel(series, metric, dom, range, now);
  var plot = lay.plot;
  var out = [];
  out.push(
      '<svg class="panel-chart" data-panel="' + esc(id) + '" viewBox="0 0 '
    + PANEL.width + ' ' + PANEL.height + '" role="img" tabindex="0" '
    + 'aria-label="' + esc(title + ': ' + METRICS[metric].label) + '">'
    );
  [1, 0.5].forEach(function (f) {
    var y = round(plot.y1 - f * (plot.y1 - plot.y0));
    out.push(
        '<line class="grid" x1="' + plot.x0 + '" x2="' + plot.x1 + '" y1="'
      + y + '" y2="' + y + '"/>'
      );
    out.push(
        '<text class="tick" x="' + (plot.x0 - 6) + '" y="' + y
      + '" text-anchor="end" dominant-baseline="middle">'
      + esc(formatNumber(f * lay.ymax, metric)) + '</text>'
      );
  });
  out.push(
      '<line class="axis" x1="' + plot.x0 + '" x2="' + plot.x1 + '" y1="'
    + plot.y1 + '" y2="' + plot.y1 + '"/>'
    );
  if (dom) {
    var ty = PANEL.height - 7;
    out.push(
        '<text class="tick" x="' + plot.x0 + '" y="' + ty + '">'
      + esc(formatDate(dom.first)) + '</text>'
      );
    if (dom.last !== dom.first) {
      out.push(
          '<text class="tick" x="' + plot.x1 + '" y="' + ty
        + '" text-anchor="end">' + esc(formatDate(dom.last)) + '</text>'
        );
    }
  }
  var segments = [], current = [];
  lay.marks.forEach(function (m) {
    if (m.value == null) {
      if (current.length) {
        segments.push(current);
      }
      current = [];
    } else {
      current.push(m);
    }
  });
  if (current.length) {
    segments.push(current);
  }
  segments.forEach(function (seg) {
    if (seg.length === 1) {
      out.push(
          '<circle class="lone" cx="' + seg[0].x + '" cy="' + seg[0].y
        + '" r="2.5"/>'
        );
    } else {
      out.push(
          '<path class="line" d="M' + seg.map(function (m) {
            return m.x + ' ' + m.y;
          }).join(' L') + '"/>'
        );
    }
  });
  lay.marks.forEach(function (m) {
    if (m.changed) {
      out.push(
          '<circle class="changed" cx="' + m.x + '" cy="' + m.y + '" r="3.5"/>'
        );
    }
    if (m.point.status !== 'ok') {
      out.push(
          '<path class="fail" d="M' + (m.x - 3) + ' ' + (plot.y1 - 3)
        + ' l6 6 M' + (m.x + 3) + ' ' + (plot.y1 - 3) + ' l-6 6"/>'
        );
    }
  });
  var last = null;
  for (var i = lay.marks.length - 1; i >= 0; i--) {
    if (lay.marks[i].value != null) {
      last = lay.marks[i];
      break;
    }
  }
  if (last) {
    out.push(
        '<circle class="end" cx="' + last.x + '" cy="' + last.y + '" r="4"/>'
      );
    out.push(
        '<text class="end-label" x="' + (last.x + 8) + '" y="' + last.y
      + '" dominant-baseline="middle">' + esc(formatValue(last.value, metric))
      + '</text>'
      );
  }
  if (!lay.marks.length) {
    out.push(
        '<text class="empty" x="' + round((plot.x0 + plot.x1) / 2) + '" y="'
      + round((plot.y0 + plot.y1) / 2) + '" text-anchor="middle">'
      + 'no runs in this range</text>'
      );
  }
  out.push(
      '<g class="cursor" hidden><line class="crosshair" x1="0" x2="0" y1="'
    + plot.y0 + '" y2="' + plot.y1 + '"/><circle class="cursor-dot" r="4"/>'
    + '</g>'
    );
  out.push(
      '<rect class="hit" x="' + plot.x0 + '" y="' + plot.y0 + '" width="'
    + (plot.x1 - plot.x0) + '" height="' + (plot.y1 - plot.y0) + '"/>'
    );
  out.push('</svg>');
  return {svg: out.join(''), layout: lay};
}

function summaryHtml(summary, metric) {
  if (!summary.latest) {
    return '';
  }
  var parts = [];
  if (summary.latest.value == null) {
    parts.push('<span class="status critical">failed</span>');
  }
  if (summary.ratio != null) {
    var verdict = verdictOf(summary.ratio);
    var pct = Math.round((summary.ratio - 1) * 100);
    var text = (pct > 0 ? '+' : '') + pct + '%'
             + (verdict === 'same' ? '' : ' ' + verdict);
    parts.push(
        '<span class="delta ' + verdict + '" title="against the previous run">'
      + esc(text) + '</span>'
      );
  }
  if (stepsChanged(summary)) {
    parts.push('<span class="note">steps changed</span>');
  }
  return parts.join(' ');
}

function tableHtml(suite, seriesList, metric, backends) {
  var out = [];
  out.push(
      '<table class="table-view" id="table-' + esc(suite) + '" hidden>'
    + '<caption>' + esc(suite) + ': the last run of every item against the '
    + 'previous one (' + esc(METRICS[metric].label) + ')</caption>'
    + '<thead><tr><th>item</th><th>date</th><th>commit</th><th>value</th>'
    + '<th>previous</th><th>ratio</th><th>steps</th><th>status</th></tr>'
    + '</thead><tbody>'
    );
  seriesList.forEach(function (s) {
    var sm = latestOf(s, metric), a = sm.latest, b = sm.previous;
    if (!a) {
      return;
    }
    var steps = a.point.steps == null
        ? '-' : formatNumber(a.point.steps, 'steps');
    if (stepsChanged(sm)) {
      steps += ' (changed from ' + formatNumber(b.point.steps, 'steps') + ')';
    }
    var ratio = sm.ratio == null
        ? '-' : sm.ratio.toFixed(2) + ' ' + verdictOf(sm.ratio);
    var status = a.point.status + (a.point.error ? ': ' + a.point.error : '');
    out.push(
        '<tr><td>' + esc(titleOf(s, backends)) + '</td><td>'
      + esc(formatDate(a.point.date)) + '</td><td><code>'
      + esc(a.point.commit || '-') + '</code></td><td class="num">'
      + esc(formatValue(a.value, metric)) + '</td><td class="num">'
      + esc(b ? formatValue(b.value, metric) : '-') + '</td><td class="num">'
      + esc(ratio) + '</td><td class="num">' + esc(steps) + '</td><td>'
      + esc(status) + '</td></tr>'
      );
  });
  out.push('</tbody></table>');
  return out.join('');
}

function figureHtml(suite, seriesList, options, registry) {
  var metric = metricOf(suite, options.metric);
  var dom = domainOf(seriesList, options.range, options.now);
  var backends = backendsOf(seriesList).length;
  var out = [];
  out.push('<figure class="suite" id="suite-' + esc(suite) + '">');
  out.push(
      '<figcaption><h2>' + esc(suite) + '</h2><p>'
    + esc(DESCRIPTIONS[suite] || '') + ' Metric: '
    + esc(METRICS[metric].label) + '.</p><p class="actions">'
    + '<button type="button" class="table-toggle" data-suite="' + esc(suite)
    + '" aria-controls="table-' + esc(suite) + '" aria-expanded="false">'
    + 'Table</button></p></figcaption>'
    );
  out.push('<div class="panels">');
  seriesList.forEach(function (s, i) {
    var id = suite + '-' + i;
    var title = titleOf(s, backends);
    var panel = panelSvg(s, metric, dom, options.range, options.now, id, title);
    if (registry) {
      registry[id] = {series: s, metric: metric, layout: panel.layout};
    }
    out.push(
        '<div class="panel"><h3><span class="name">' + esc(title) + '</span> '
      + summaryHtml(latestOf(s, metric), metric) + '</h3>' + panel.svg
      + '</div>'
      );
  });
  out.push('</div>');
  out.push(tableHtml(suite, seriesList, metric, backends));
  out.push('</figure>');
  return out.join('');
}

/*
 * The figures of the page, one per suite, as HTML.  ``options`` holds the
 * metric ('default' or a key of METRICS), the range (a key of RANGES), and
 * the time ``now`` of the range.  ``registry`` receives the series, the
 * metric, and the layout of every panel by its id, for the hover layer.
 */
function renderPage(points, options, registry) {
  options = options || {};
  var opts = {
      metric: options.metric || 'default', range: options.range || 'all'
    , now: options.now || Date.now()
    };
  var all = groupSeries(points);
  var suites = [];
  all.forEach(function (s) {
    if (suites.indexOf(s.suite) < 0) {
      suites.push(s.suite);
    }
  });
  if (!suites.length) {
    return '<p class="empty">The history has no records yet.</p>';
  }
  return suites.map(function (suite) {
    var list = all.filter(function (s) { return s.suite === suite; });
    return figureHtml(suite, list, opts, registry);
  }).join('\n');
}

/* One line about the points for the status line of the page. */
function describe(points) {
  if (!points.length) {
    return 'The history has no records yet.';
  }
  var first = points[0].date, last = points[0].date;
  points.forEach(function (p) {
    if (p.date < first) {
      first = p.date;
    }
    if (p.date > last) {
      last = p.date;
    }
  });
  return points.length + ' records from ' + formatDate(first) + ' to '
       + formatDate(last) + '.';
}

/* The DOM glue: the fetch, the controls, the hover layer, the tables. */
function main() {
  var doc = root.document;
  var charts = doc.getElementById('charts');
  var status = doc.getElementById('status');
  var metricSelect = doc.getElementById('metric');
  var rangeSelect = doc.getElementById('range');
  var dataLink = doc.getElementById('data-link');
  var tooltip = doc.getElementById('tooltip');
  var state = {points: [], registry: {}, active: null};

  function line(text) {
    var div = doc.createElement('div');
    div.textContent = text;
    tooltip.appendChild(div);
  }

  function showTooltip(entry, mark, clientX, clientY) {
    var p = mark.point;
    tooltip.textContent = '';
    var value = doc.createElement('strong');
    value.textContent = mark.value == null
        ? 'no value' : formatValue(mark.value, entry.metric);
    tooltip.appendChild(value);
    tooltip.appendChild(doc.createTextNode(' ' + METRICS[entry.metric].label));
    line(formatDate(p.date) + (p.commit ? ' · ' + p.commit : ''));
    if (p.steps != null) {
      var counters = 'steps ' + formatNumber(p.steps, 'steps');
      if (p.forks != null) {
        counters += ' · forks ' + formatNumber(p.forks, 'forks');
      }
      if (mark.changed) {
        counters += ' · changed from '
                  + formatNumber(mark.previousSteps, 'steps');
      }
      line(counters);
    }
    line(
        p.status === 'ok'
          ? 'status ok'
          : 'status ' + p.status + (p.error ? ': ' + p.error : '')
      );
    if (p.label) {
      line(p.label);
    }
    tooltip.hidden = false;
    var w = tooltip.offsetWidth, h = tooltip.offsetHeight;
    var x = clientX + 14, y = clientY + 14;
    if (x + w > root.innerWidth - 8) {
      x = clientX - w - 14;
    }
    if (y + h > root.innerHeight - 8) {
      y = clientY - h - 14;
    }
    tooltip.style.left = Math.max(4, x) + 'px';
    tooltip.style.top = Math.max(4, y) + 'px';
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  function cursorTo(svg, entry, index, clientX, clientY) {
    var marks = entry.layout.marks;
    var cursor = svg.querySelector('.cursor');
    if (!marks.length || index < 0 || index >= marks.length) {
      cursor.hidden = true;
      hideTooltip();
      return;
    }
    var mark = marks[index];
    entry.cursor = index;
    var hair = cursor.querySelector('.crosshair');
    var dot = cursor.querySelector('.cursor-dot');
    hair.setAttribute('x1', mark.x);
    hair.setAttribute('x2', mark.x);
    dot.setAttribute('cx', mark.x);
    dot.setAttribute('cy', mark.y);
    cursor.hidden = false;
    if (clientX == null) {
      var box = svg.getBoundingClientRect();
      var scale = box.width / PANEL.width;
      clientX = box.left + mark.x * scale;
      clientY = box.top + mark.y * scale;
    }
    showTooltip(entry, mark, clientX, clientY);
  }

  function nearest(svg, entry, clientX) {
    var ctm = svg.getScreenCTM();
    if (!ctm) {
      return -1;
    }
    var x = (clientX - ctm.e) / ctm.a;
    var best = -1, distance = Infinity;
    entry.layout.marks.forEach(function (m, i) {
      var d = Math.abs(m.x - x);
      if (d < distance) {
        distance = d;
        best = i;
      }
    });
    return best;
  }

  function leave(svg) {
    svg.querySelector('.cursor').hidden = true;
    hideTooltip();
  }

  function attach() {
    var panels = charts.querySelectorAll('svg[data-panel]');
    Array.prototype.forEach.call(panels, function (svg) {
      var entry = state.registry[svg.getAttribute('data-panel')];
      if (!entry) {
        return;
      }
      entry.cursor = entry.layout.marks.length - 1;
      svg.addEventListener('pointermove', function (event) {
        cursorTo(svg, entry, nearest(svg, entry, event.clientX), event.clientX
                 , event.clientY);
      });
      svg.addEventListener('pointerleave', function () { leave(svg); });
      svg.addEventListener('focus', function () {
        cursorTo(svg, entry, entry.cursor);
      });
      svg.addEventListener('blur', function () { leave(svg); });
      svg.addEventListener('keydown', function (event) {
        var n = entry.layout.marks.length;
        if (event.key === 'ArrowLeft' && n) {
          cursorTo(svg, entry, Math.max(0, entry.cursor - 1));
        } else if (event.key === 'ArrowRight' && n) {
          cursorTo(svg, entry, Math.min(n - 1, entry.cursor + 1));
        } else if (event.key === 'Escape') {
          leave(svg);
        } else {
          return;
        }
        event.preventDefault();
      });
    });
    var toggles = charts.querySelectorAll('button.table-toggle');
    Array.prototype.forEach.call(toggles, function (button) {
      button.addEventListener('click', function () {
        var table = doc.getElementById(button.getAttribute('aria-controls'));
        var open = table.hidden;
        table.hidden = !open;
        button.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });
  }

  function render() {
    state.registry = {};
    charts.innerHTML = renderPage(
        state.points, {metric: metricSelect.value, range: rangeSelect.value}
      , state.registry
      );
    attach();
  }

  function fail(urls, reason) {
    status.textContent = 'No history found (' + reason + ').  Looked for '
                       + urls.join(', ') + '.';
    charts.innerHTML = '<p class="empty">The nightly job writes points.json '
                     + 'to the branch ' + esc(BRANCH) + ' of the repository; '
                     + 'the page reads it from there on GitHub Pages, from a '
                     + 'file beside itself elsewhere, or from the URL of '
                     + '?history=.</p>';
  }

  function load(urls, i, reason) {
    if (i >= urls.length) {
      fail(urls, reason || 'no URL answered');
      return;
    }
    root.fetch(urls[i], {cache: 'no-cache'}).then(function (response) {
      if (!response.ok) {
        throw new Error(urls[i] + ': HTTP ' + response.status);
      }
      return response.json();
    }).then(function (data) {
      if (!data || !Array.isArray(data.points)) {
        throw new Error(urls[i] + ': not a points file');
      }
      state.points = data.points;
      dataLink.href = urls[i];
      dataLink.textContent = urls[i];
      status.textContent = describe(data.points)
                         + (data.generated
                              ? ' Written ' + formatDate(data.generated) + '.'
                              : '');
      render();
    }).catch(function (error) {
      load(urls, i + 1, String(error && error.message || error));
    });
  }

  metricSelect.addEventListener('change', render);
  rangeSelect.addEventListener('change', render);
  load(historyUrls(root.location, doc.body.getAttribute('data-history')), 0);
}

var perf = {
    BRANCH: BRANCH, METRICS: METRICS, RANGES: RANGES, SUITES: SUITES
  , THRESHOLD: THRESHOLD, describe: describe, domainOf: domainOf
  , formatNumber: formatNumber, formatValue: formatValue
  , groupSeries: groupSeries, historyUrls: historyUrls, latestOf: latestOf
  , layoutPanel: layoutPanel, metricOf: metricOf, niceCeiling: niceCeiling
  , renderPage: renderPage, valueOf: valueOf, verdictOf: verdictOf
  };
root.perf = perf;
if (typeof module !== 'undefined' && module.exports) {
  module.exports = perf;
}
if (typeof root.document !== 'undefined' && root.document.getElementById) {
  if (root.document.readyState === 'loading') {
    root.document.addEventListener('DOMContentLoaded', main);
  } else if (root.document.getElementById('charts')) {
    main();
  }
}
})(typeof window !== 'undefined' ? window : globalThis);
