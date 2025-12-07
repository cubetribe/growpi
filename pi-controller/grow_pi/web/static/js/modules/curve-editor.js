/**
 * curve-editor.js - Interactive Bezier Curve Editor Module
 *
 * A visual curve editor similar to Cubase automation or BIOS fan curves.
 * Features:
 * - Draggable keyframe anchor points
 * - Bezier/Catmull-Rom spline interpolation
 * - Touch + Mouse support
 * - Mobile fullscreen editing mode
 * - Real-time table synchronization
 *
 * NO React/Vue - Pure Vanilla JS + SVG
 * NO Canvas with 60fps loop - Event-based updates only
 */

// ============================================================================
// CONSTANTS
// ============================================================================

const EDITOR_CONFIG = {
    // SVG dimensions (will be scaled responsively)
    width: 400,
    height: 200,
    padding: { top: 20, right: 20, bottom: 30, left: 45 },

    // Keyframe styling
    keyframeRadius: 10,
    keyframeRadiusTouch: 14, // Larger for touch devices
    keyframeStrokeWidth: 2,

    // Curve styling
    curveStrokeWidth: 2.5,
    curveStrokeWidthHover: 3,

    // Grid
    gridLinesX: 8, // Every 3 hours
    gridLinesY: 4, // 0%, 25%, 50%, 75%, 100%

    // Interaction
    snapToGridTime: 15, // minutes
    snapToGridIntensity: 5, // percent
    longPressDeleteMs: 800, // ms for long-press delete on mobile
    doubleTapDeleteMs: 300, // ms for double-tap delete

    // Animation
    transitionDuration: '0.15s',
};

// Channel colors (matching curves.js)
const CHANNEL_COLORS = {
    1: '#ff4444', // Far Red
    2: '#ffbb44', // Warm White
    3: '#88ddff', // Cool White
    4: '#cc66ff', // UV
};

const CHANNEL_NAMES = {
    1: 'Far Red',
    2: 'Warm White',
    3: 'Cool White',
    4: 'UV',
};

// ============================================================================
// CURVE EDITOR CLASS
// ============================================================================

/**
 * BezierCurveEditor - Interactive SVG-based curve editor
 */
export class BezierCurveEditor {
    /**
     * Create a new curve editor
     * @param {HTMLElement} container - Container element for the editor
     * @param {number} channel - Channel number (1-4)
     * @param {Object} options - Configuration options
     */
    constructor(container, channel, options = {}) {
        this.container = container;
        this.channel = channel;
        this.color = CHANNEL_COLORS[channel] || '#11ff55';
        this.name = CHANNEL_NAMES[channel] || `Channel ${channel}`;

        // Merge options with defaults
        this.config = { ...EDITOR_CONFIG, ...options };

        // State
        this.points = []; // Array of {time: "HH:MM", intensity: number}
        this.isFullscreen = false;
        this.isDragging = false;
        this.dragPointIndex = null;
        this.lastTapTime = 0;
        this.longPressTimer = null;

        // Callbacks
        this.onChangeCallback = null;
        this.onSaveCallback = null;

        // DOM elements
        this.svg = null;
        this.curveGroup = null;
        this.pointsGroup = null;
        this.fullscreenOverlay = null;

        // Touch handling
        this.touchStartPos = null;
        this.activePointerId = null;

        // Initialize
        this._init();
    }

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    /**
     * Initialize the editor
     */
    _init() {
        this._createDOM();
        this._attachEventListeners();
        this._render();
    }

    /**
     * Create the DOM structure
     */
    _createDOM() {
        // Clear container
        this.container.innerHTML = '';
        this.container.classList.add('curve-editor-container');

        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'curve-editor-wrapper';

        // Create SVG
        const { width, height } = this.config;
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('class', 'curve-editor-svg');
        this.svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        this.svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

        // Add defs for gradients and filters
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <linearGradient id="curveGradient-${this.channel}" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:${this.color};stop-opacity:0.4" />
                <stop offset="100%" style="stop-color:${this.color};stop-opacity:0.05" />
            </linearGradient>
            <filter id="glow-${this.channel}" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
            <filter id="shadow-${this.channel}">
                <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="rgba(0,0,0,0.5)"/>
            </filter>
        `;
        this.svg.appendChild(defs);

        // Create groups in correct z-order
        this.gridGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.gridGroup.setAttribute('class', 'curve-editor-grid');

        this.fillGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.fillGroup.setAttribute('class', 'curve-editor-fill');

        this.curveGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.curveGroup.setAttribute('class', 'curve-editor-curve');

        this.pointsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.pointsGroup.setAttribute('class', 'curve-editor-points');

        this.labelsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.labelsGroup.setAttribute('class', 'curve-editor-labels');

        this.svg.appendChild(this.gridGroup);
        this.svg.appendChild(this.fillGroup);
        this.svg.appendChild(this.curveGroup);
        this.svg.appendChild(this.pointsGroup);
        this.svg.appendChild(this.labelsGroup);

        wrapper.appendChild(this.svg);

        // Create toolbar
        const toolbar = document.createElement('div');
        toolbar.className = 'curve-editor-toolbar';
        toolbar.innerHTML = `
            <button class="curve-editor-btn fullscreen-btn" title="Vollbild bearbeiten">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                    <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                </svg>
                Vollbild
            </button>
            <span class="curve-editor-hint">Klicken zum Punkt setzen | Ziehen zum Verschieben | Doppelklick zum Loeschen</span>
        `;
        wrapper.appendChild(toolbar);

        this.container.appendChild(wrapper);

        // Store references
        this.fullscreenBtn = toolbar.querySelector('.fullscreen-btn');
    }

    /**
     * Attach event listeners
     */
    _attachEventListeners() {
        // SVG click to add point
        this.svg.addEventListener('click', this._handleSvgClick.bind(this));

        // Mouse events for dragging
        this.svg.addEventListener('mousedown', this._handleMouseDown.bind(this));
        document.addEventListener('mousemove', this._handleMouseMove.bind(this));
        document.addEventListener('mouseup', this._handleMouseUp.bind(this));

        // Touch events for mobile
        this.svg.addEventListener('touchstart', this._handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this._handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this._handleTouchEnd.bind(this));
        document.addEventListener('touchcancel', this._handleTouchEnd.bind(this));

        // Fullscreen button
        if (this.fullscreenBtn) {
            this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        }

        // Keyboard accessibility
        this.svg.setAttribute('tabindex', '0');
        this.svg.addEventListener('keydown', this._handleKeyDown.bind(this));

        // Window resize for responsive SVG
        window.addEventListener('resize', () => this._render());
    }

    // ========================================================================
    // COORDINATE TRANSFORMATION
    // ========================================================================

    /**
     * Convert time string to X coordinate
     * @param {string} time - Time in "HH:MM" format
     * @returns {number} X coordinate in SVG space
     */
    _timeToX(time) {
        const [hours, minutes] = time.split(':').map(Number);
        const totalMinutes = hours * 60 + minutes;
        const { width, padding } = this.config;
        const chartWidth = width - padding.left - padding.right;
        return padding.left + (totalMinutes / (24 * 60)) * chartWidth;
    }

    /**
     * Convert X coordinate to time string
     * @param {number} x - X coordinate in SVG space
     * @returns {string} Time in "HH:MM" format
     */
    _xToTime(x) {
        const { width, padding } = this.config;
        const chartWidth = width - padding.left - padding.right;
        const clampedX = Math.max(padding.left, Math.min(x, padding.left + chartWidth));
        const ratio = (clampedX - padding.left) / chartWidth;
        let totalMinutes = Math.round(ratio * 24 * 60);

        // Snap to grid
        const snap = this.config.snapToGridTime;
        totalMinutes = Math.round(totalMinutes / snap) * snap;
        totalMinutes = Math.max(0, Math.min(totalMinutes, 24 * 60 - 1));

        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }

    /**
     * Convert intensity to Y coordinate
     * @param {number} intensity - Intensity 0-100
     * @returns {number} Y coordinate in SVG space
     */
    _intensityToY(intensity) {
        const { height, padding } = this.config;
        const chartHeight = height - padding.top - padding.bottom;
        // Y is inverted (0 at top)
        return padding.top + chartHeight - (intensity / 100) * chartHeight;
    }

    /**
     * Convert Y coordinate to intensity
     * @param {number} y - Y coordinate in SVG space
     * @returns {number} Intensity 0-100
     */
    _yToIntensity(y) {
        const { height, padding } = this.config;
        const chartHeight = height - padding.top - padding.bottom;
        const clampedY = Math.max(padding.top, Math.min(y, padding.top + chartHeight));
        const ratio = 1 - (clampedY - padding.top) / chartHeight;
        let intensity = Math.round(ratio * 100);

        // Snap to grid
        const snap = this.config.snapToGridIntensity;
        intensity = Math.round(intensity / snap) * snap;
        return Math.max(0, Math.min(intensity, 100));
    }

    /**
     * Get SVG coordinates from mouse/touch event
     * @param {MouseEvent|Touch} event - Event with clientX/clientY
     * @returns {{x: number, y: number}} SVG coordinates
     */
    _getSvgCoords(event) {
        const rect = this.svg.getBoundingClientRect();
        const { width, height } = this.config;

        // Scale from screen coords to SVG viewBox coords
        const scaleX = width / rect.width;
        const scaleY = height / rect.height;

        return {
            x: (event.clientX - rect.left) * scaleX,
            y: (event.clientY - rect.top) * scaleY,
        };
    }

    // ========================================================================
    // RENDERING
    // ========================================================================

    /**
     * Render the entire editor
     */
    _render() {
        this._renderGrid();
        this._renderLabels();
        this._renderCurve();
        this._renderPoints();
    }

    /**
     * Render the background grid
     */
    _renderGrid() {
        this.gridGroup.innerHTML = '';
        const { width, height, padding, gridLinesX, gridLinesY } = this.config;
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Horizontal grid lines
        for (let i = 0; i <= gridLinesY; i++) {
            const y = padding.top + (i / gridLinesY) * chartHeight;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', padding.left);
            line.setAttribute('y1', y);
            line.setAttribute('x2', padding.left + chartWidth);
            line.setAttribute('y2', y);
            line.setAttribute('class', 'grid-line horizontal');
            this.gridGroup.appendChild(line);
        }

        // Vertical grid lines
        for (let i = 0; i <= gridLinesX; i++) {
            const x = padding.left + (i / gridLinesX) * chartWidth;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x);
            line.setAttribute('y1', padding.top);
            line.setAttribute('x2', x);
            line.setAttribute('y2', padding.top + chartHeight);
            line.setAttribute('class', 'grid-line vertical');
            this.gridGroup.appendChild(line);
        }

        // Border
        const border = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        border.setAttribute('x', padding.left);
        border.setAttribute('y', padding.top);
        border.setAttribute('width', chartWidth);
        border.setAttribute('height', chartHeight);
        border.setAttribute('class', 'grid-border');
        this.gridGroup.appendChild(border);
    }

    /**
     * Render axis labels
     */
    _renderLabels() {
        this.labelsGroup.innerHTML = '';
        const { width, height, padding, gridLinesX, gridLinesY } = this.config;
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Y-axis labels (intensity)
        const yLabels = ['100%', '75%', '50%', '25%', '0%'];
        for (let i = 0; i <= gridLinesY; i++) {
            const y = padding.top + (i / gridLinesY) * chartHeight;
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', padding.left - 5);
            text.setAttribute('y', y + 4);
            text.setAttribute('class', 'axis-label y-label');
            text.textContent = yLabels[i];
            this.labelsGroup.appendChild(text);
        }

        // X-axis labels (time)
        const timeLabels = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '24:00'];
        for (let i = 0; i <= gridLinesX; i++) {
            const x = padding.left + (i / gridLinesX) * chartWidth;
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x);
            text.setAttribute('y', height - padding.bottom + 15);
            text.setAttribute('class', 'axis-label x-label');
            text.textContent = timeLabels[i];
            this.labelsGroup.appendChild(text);
        }
    }

    /**
     * Render the Bezier curve
     */
    _renderCurve() {
        this.curveGroup.innerHTML = '';
        this.fillGroup.innerHTML = '';

        if (this.points.length === 0) {
            return;
        }

        // Sort points by time
        const sortedPoints = this._getSortedPoints();

        // Generate path
        const pathData = this._generateBezierPath(sortedPoints);

        // Create fill area
        const { height, padding } = this.config;
        const chartBottom = height - padding.bottom;
        const firstX = this._timeToX(sortedPoints[0].time);
        const lastX = this._timeToX(sortedPoints[sortedPoints.length - 1].time);

        const fillPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        fillPath.setAttribute('d', `${pathData} L${lastX},${chartBottom} L${firstX},${chartBottom} Z`);
        fillPath.setAttribute('class', 'curve-fill');
        fillPath.setAttribute('fill', `url(#curveGradient-${this.channel})`);
        this.fillGroup.appendChild(fillPath);

        // Create curve line
        const curvePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        curvePath.setAttribute('d', pathData);
        curvePath.setAttribute('class', 'curve-line');
        curvePath.setAttribute('stroke', this.color);
        curvePath.setAttribute('stroke-width', this.config.curveStrokeWidth);
        curvePath.setAttribute('filter', `url(#glow-${this.channel})`);
        this.curveGroup.appendChild(curvePath);
    }

    /**
     * Generate SVG path data using Catmull-Rom to Bezier conversion
     * @param {Array} points - Sorted array of {time, intensity}
     * @returns {string} SVG path data
     */
    _generateBezierPath(points) {
        if (points.length === 0) return '';
        if (points.length === 1) {
            const x = this._timeToX(points[0].time);
            const y = this._intensityToY(points[0].intensity);
            return `M${x},${y}`;
        }

        // Convert to coordinate pairs
        const coords = points.map((p) => ({
            x: this._timeToX(p.time),
            y: this._intensityToY(p.intensity),
        }));

        // Start path
        let path = `M${coords[0].x},${coords[0].y}`;

        if (coords.length === 2) {
            // Just draw a line for 2 points
            path += ` L${coords[1].x},${coords[1].y}`;
            return path;
        }

        // Use Catmull-Rom to Bezier conversion for smooth curves
        // Tension factor (0 = sharp, 1 = very smooth)
        const tension = 0.3;

        for (let i = 0; i < coords.length - 1; i++) {
            const p0 = coords[Math.max(0, i - 1)];
            const p1 = coords[i];
            const p2 = coords[i + 1];
            const p3 = coords[Math.min(coords.length - 1, i + 2)];

            // Catmull-Rom to Bezier control points
            const cp1x = p1.x + ((p2.x - p0.x) * tension) / 3;
            const cp1y = p1.y + ((p2.y - p0.y) * tension) / 3;
            const cp2x = p2.x - ((p3.x - p1.x) * tension) / 3;
            const cp2y = p2.y - ((p3.y - p1.y) * tension) / 3;

            path += ` C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
        }

        return path;
    }

    /**
     * Render keyframe points
     */
    _renderPoints() {
        this.pointsGroup.innerHTML = '';

        const isTouchDevice = 'ontouchstart' in window;
        const radius = isTouchDevice ? this.config.keyframeRadiusTouch : this.config.keyframeRadius;

        this.points.forEach((point, index) => {
            const x = this._timeToX(point.time);
            const y = this._intensityToY(point.intensity);

            // Create group for point
            const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            group.setAttribute('class', 'keyframe-group');
            group.setAttribute('data-index', index);
            group.setAttribute('transform', `translate(${x}, ${y})`);
            group.style.cursor = 'grab';

            // Outer glow circle
            const glow = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            glow.setAttribute('r', radius + 4);
            glow.setAttribute('class', 'keyframe-glow');
            glow.setAttribute('fill', this.color);
            glow.setAttribute('opacity', '0.2');
            group.appendChild(glow);

            // Main circle
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', radius);
            circle.setAttribute('class', 'keyframe-circle');
            circle.setAttribute('fill', '#fff');
            circle.setAttribute('stroke', this.color);
            circle.setAttribute('stroke-width', this.config.keyframeStrokeWidth);
            circle.setAttribute('filter', `url(#shadow-${this.channel})`);
            group.appendChild(circle);

            // Inner dot
            const inner = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            inner.setAttribute('r', radius * 0.4);
            inner.setAttribute('class', 'keyframe-inner');
            inner.setAttribute('fill', this.color);
            group.appendChild(inner);

            // Tooltip showing values
            const tooltip = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            tooltip.setAttribute('y', -(radius + 10));
            tooltip.setAttribute('class', 'keyframe-tooltip');
            tooltip.textContent = `${point.time} | ${point.intensity}%`;
            group.appendChild(tooltip);

            this.pointsGroup.appendChild(group);
        });
    }

    /**
     * Get points sorted by time
     * @returns {Array} Sorted points
     */
    _getSortedPoints() {
        return [...this.points].sort((a, b) => {
            const [ah, am] = a.time.split(':').map(Number);
            const [bh, bm] = b.time.split(':').map(Number);
            return ah * 60 + am - (bh * 60 + bm);
        });
    }

    // ========================================================================
    // EVENT HANDLERS
    // ========================================================================

    /**
     * Handle SVG click to add new point
     * @param {MouseEvent} event
     */
    _handleSvgClick(event) {
        // Don't add point if we were dragging or clicking on existing point
        if (this.isDragging || event.target.closest('.keyframe-group')) {
            return;
        }

        const coords = this._getSvgCoords(event);
        const time = this._xToTime(coords.x);
        const intensity = this._yToIntensity(coords.y);

        // Check if we're within the chart area
        const { padding, width, height } = this.config;
        if (
            coords.x < padding.left ||
            coords.x > width - padding.right ||
            coords.y < padding.top ||
            coords.y > height - padding.bottom
        ) {
            return;
        }

        this._addPoint(time, intensity);
    }

    /**
     * Handle mouse down on keyframe
     * @param {MouseEvent} event
     */
    _handleMouseDown(event) {
        const group = event.target.closest('.keyframe-group');
        if (!group) return;

        event.preventDefault();
        const index = parseInt(group.dataset.index, 10);

        // Check for double-click to delete
        const now = Date.now();
        if (now - this.lastTapTime < this.config.doubleTapDeleteMs) {
            this._removePoint(index);
            this.lastTapTime = 0;
            return;
        }
        this.lastTapTime = now;

        // Start dragging
        this.isDragging = true;
        this.dragPointIndex = index;
        group.style.cursor = 'grabbing';
        group.classList.add('dragging');

        // Add class to SVG for styling
        this.svg.classList.add('is-dragging');
    }

    /**
     * Handle mouse move during drag
     * @param {MouseEvent} event
     */
    _handleMouseMove(event) {
        if (!this.isDragging || this.dragPointIndex === null) return;

        event.preventDefault();
        const coords = this._getSvgCoords(event);
        const time = this._xToTime(coords.x);
        const intensity = this._yToIntensity(coords.y);

        // Update point
        this.points[this.dragPointIndex] = { time, intensity };

        // Re-render curve and update point position
        this._renderCurve();
        this._updatePointPosition(this.dragPointIndex, coords);

        // Trigger change callback (debounced save happens on mouseup)
        if (this.onChangeCallback) {
            this.onChangeCallback(this.points);
        }
    }

    /**
     * Handle mouse up
     * @param {MouseEvent} event
     */
    _handleMouseUp(event) {
        if (!this.isDragging) return;

        const group = this.pointsGroup.querySelector(`[data-index="${this.dragPointIndex}"]`);
        if (group) {
            group.style.cursor = 'grab';
            group.classList.remove('dragging');
        }

        this.isDragging = false;
        this.dragPointIndex = null;
        this.svg.classList.remove('is-dragging');

        // Full re-render to ensure correct state
        this._render();

        // Trigger save callback
        if (this.onSaveCallback) {
            this.onSaveCallback(this.points);
        }
    }

    /**
     * Handle touch start
     * @param {TouchEvent} event
     */
    _handleTouchStart(event) {
        const touch = event.touches[0];
        const group = document.elementFromPoint(touch.clientX, touch.clientY)?.closest('.keyframe-group');

        if (!group) {
            // Check if we should add a point (single tap on empty area)
            // We'll handle this in touchend to distinguish from scrolling
            this.touchStartPos = { x: touch.clientX, y: touch.clientY };
            return;
        }

        event.preventDefault();
        const index = parseInt(group.dataset.index, 10);
        this.activePointerId = touch.identifier;

        // Start long-press timer for deletion
        this.longPressTimer = setTimeout(() => {
            this._removePoint(index);
            this.longPressTimer = null;
            this.isDragging = false;
        }, this.config.longPressDeleteMs);

        // Start dragging
        this.isDragging = true;
        this.dragPointIndex = index;
        group.classList.add('dragging');
        this.svg.classList.add('is-dragging');
    }

    /**
     * Handle touch move
     * @param {TouchEvent} event
     */
    _handleTouchMove(event) {
        // Cancel long-press if moving
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

        if (!this.isDragging || this.dragPointIndex === null) return;

        // Find the correct touch
        const touch = Array.from(event.touches).find((t) => t.identifier === this.activePointerId);
        if (!touch) return;

        event.preventDefault();
        const coords = this._getSvgCoords(touch);
        const time = this._xToTime(coords.x);
        const intensity = this._yToIntensity(coords.y);

        // Update point
        this.points[this.dragPointIndex] = { time, intensity };

        // Re-render
        this._renderCurve();
        this._updatePointPosition(this.dragPointIndex, coords);

        if (this.onChangeCallback) {
            this.onChangeCallback(this.points);
        }
    }

    /**
     * Handle touch end
     * @param {TouchEvent} event
     */
    _handleTouchEnd(event) {
        // Cancel long-press timer
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

        // Check if this was a tap to add a point
        if (this.touchStartPos && !this.isDragging && event.changedTouches.length > 0) {
            const touch = event.changedTouches[0];
            const dx = Math.abs(touch.clientX - this.touchStartPos.x);
            const dy = Math.abs(touch.clientY - this.touchStartPos.y);

            // If movement was minimal, it's a tap
            if (dx < 10 && dy < 10) {
                const coords = this._getSvgCoords(touch);
                const { padding, width, height } = this.config;

                if (
                    coords.x >= padding.left &&
                    coords.x <= width - padding.right &&
                    coords.y >= padding.top &&
                    coords.y <= height - padding.bottom
                ) {
                    const time = this._xToTime(coords.x);
                    const intensity = this._yToIntensity(coords.y);
                    this._addPoint(time, intensity);
                }
            }
        }

        this.touchStartPos = null;

        if (!this.isDragging) return;

        const group = this.pointsGroup.querySelector(`[data-index="${this.dragPointIndex}"]`);
        if (group) {
            group.classList.remove('dragging');
        }

        this.isDragging = false;
        this.dragPointIndex = null;
        this.activePointerId = null;
        this.svg.classList.remove('is-dragging');

        this._render();

        if (this.onSaveCallback) {
            this.onSaveCallback(this.points);
        }
    }

    /**
     * Handle keyboard events
     * @param {KeyboardEvent} event
     */
    _handleKeyDown(event) {
        if (event.key === 'Escape' && this.isFullscreen) {
            this.toggleFullscreen();
        }
    }

    /**
     * Update single point position during drag (optimized)
     * @param {number} index - Point index
     * @param {Object} coords - SVG coordinates {x, y}
     */
    _updatePointPosition(index, coords) {
        const group = this.pointsGroup.querySelector(`[data-index="${index}"]`);
        if (group) {
            group.setAttribute('transform', `translate(${coords.x}, ${coords.y})`);
            const tooltip = group.querySelector('.keyframe-tooltip');
            if (tooltip) {
                tooltip.textContent = `${this.points[index].time} | ${this.points[index].intensity}%`;
            }
        }
    }

    // ========================================================================
    // POINT MANIPULATION
    // ========================================================================

    /**
     * Add a new point
     * @param {string} time - Time in "HH:MM" format
     * @param {number} intensity - Intensity 0-100
     */
    _addPoint(time, intensity) {
        // Check if a point already exists at this time (within 5 minutes)
        const newMinutes = this._timeToMinutes(time);
        const exists = this.points.some((p) => {
            const existingMinutes = this._timeToMinutes(p.time);
            return Math.abs(existingMinutes - newMinutes) < 5;
        });

        if (exists) {
            console.log('Point already exists near this time');
            return;
        }

        this.points.push({ time, intensity });
        this._render();

        if (this.onChangeCallback) {
            this.onChangeCallback(this.points);
        }
        if (this.onSaveCallback) {
            this.onSaveCallback(this.points);
        }
    }

    /**
     * Remove a point by index
     * @param {number} index - Point index
     */
    _removePoint(index) {
        if (index < 0 || index >= this.points.length) return;

        this.points.splice(index, 1);
        this._render();

        if (this.onChangeCallback) {
            this.onChangeCallback(this.points);
        }
        if (this.onSaveCallback) {
            this.onSaveCallback(this.points);
        }
    }

    /**
     * Convert time string to minutes
     * @param {string} time - "HH:MM"
     * @returns {number} Minutes since midnight
     */
    _timeToMinutes(time) {
        const [h, m] = time.split(':').map(Number);
        return h * 60 + m;
    }

    // ========================================================================
    // FULLSCREEN MODE
    // ========================================================================

    /**
     * Toggle fullscreen mode
     */
    toggleFullscreen() {
        if (this.isFullscreen) {
            this._exitFullscreen();
        } else {
            this._enterFullscreen();
        }
    }

    /**
     * Enter fullscreen mode
     */
    _enterFullscreen() {
        // Create fullscreen overlay
        this.fullscreenOverlay = document.createElement('div');
        this.fullscreenOverlay.className = 'curve-editor-fullscreen-overlay';

        // Clone the editor into fullscreen
        const fullscreenWrapper = document.createElement('div');
        fullscreenWrapper.className = 'curve-editor-fullscreen-content';

        // Header with close button
        const header = document.createElement('div');
        header.className = 'curve-editor-fullscreen-header';
        header.innerHTML = `
            <span class="curve-editor-fullscreen-title" style="color: ${this.color}">
                ${this.name} - Kurve bearbeiten
            </span>
            <button class="curve-editor-fullscreen-close" title="Schliessen">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
            </button>
        `;
        fullscreenWrapper.appendChild(header);

        // Create larger SVG for fullscreen
        const svgClone = this.svg.cloneNode(true);
        svgClone.classList.add('curve-editor-fullscreen-svg');

        // Update viewBox for larger display
        const newWidth = 800;
        const newHeight = 400;
        svgClone.setAttribute('viewBox', `0 0 ${newWidth} ${newHeight}`);

        // Temporarily update config for fullscreen rendering
        const originalConfig = { ...this.config };
        this.config.width = newWidth;
        this.config.height = newHeight;
        this.config.padding = { top: 30, right: 30, bottom: 40, left: 55 };
        this.config.keyframeRadius = 14;
        this.config.keyframeRadiusTouch = 18;

        // Store original SVG
        const originalSvg = this.svg;
        this.svg = svgClone;

        // Re-render at fullscreen size
        this._render();

        // Restore original SVG reference
        this.svg = originalSvg;
        this.config = originalConfig;

        // Attach event listeners to clone
        this._attachFullscreenListeners(svgClone);

        // SVG container
        const svgContainer = document.createElement('div');
        svgContainer.className = 'curve-editor-fullscreen-svg-container';
        svgContainer.appendChild(svgClone);
        fullscreenWrapper.appendChild(svgContainer);

        // Instructions
        const instructions = document.createElement('div');
        instructions.className = 'curve-editor-fullscreen-instructions';
        instructions.innerHTML = `
            <span>Tippen: Punkt setzen</span>
            <span>Ziehen: Punkt verschieben</span>
            <span>Lang druecken / Doppeltippen: Punkt loeschen</span>
        `;
        fullscreenWrapper.appendChild(instructions);

        this.fullscreenOverlay.appendChild(fullscreenWrapper);
        document.body.appendChild(this.fullscreenOverlay);

        // Close button handler
        const closeBtn = header.querySelector('.curve-editor-fullscreen-close');
        closeBtn.addEventListener('click', () => this._exitFullscreen());

        // Close on overlay click
        this.fullscreenOverlay.addEventListener('click', (e) => {
            if (e.target === this.fullscreenOverlay) {
                this._exitFullscreen();
            }
        });

        // Try to lock orientation on mobile
        this._lockOrientation();

        this.isFullscreen = true;
        document.body.classList.add('curve-editor-fullscreen-active');
    }

    /**
     * Attach event listeners to fullscreen SVG
     * @param {SVGElement} svg - Fullscreen SVG element
     */
    _attachFullscreenListeners(svg) {
        // Store reference to fullscreen SVG
        this.fullscreenSvg = svg;

        // Create wrapper functions that use the correct SVG
        const handleClick = (event) => {
            if (this.isDragging || event.target.closest('.keyframe-group')) {
                return;
            }
            const originalSvg = this.svg;
            this.svg = this.fullscreenSvg;

            // Use fullscreen config temporarily
            const originalConfig = { ...this.config };
            this.config.width = 800;
            this.config.height = 400;
            this.config.padding = { top: 30, right: 30, bottom: 40, left: 55 };

            const coords = this._getSvgCoords(event);
            const time = this._xToTime(coords.x);
            const intensity = this._yToIntensity(coords.y);

            const { padding, width, height } = this.config;
            if (
                coords.x >= padding.left &&
                coords.x <= width - padding.right &&
                coords.y >= padding.top &&
                coords.y <= height - padding.bottom
            ) {
                this.config = originalConfig;
                this.svg = originalSvg;
                this._addPoint(time, intensity);
                this._renderFullscreen();
            } else {
                this.config = originalConfig;
                this.svg = originalSvg;
            }
        };

        const handleMouseDown = (event) => {
            const group = event.target.closest('.keyframe-group');
            if (!group) return;

            event.preventDefault();
            const index = parseInt(group.dataset.index, 10);

            // Check for double-click to delete
            const now = Date.now();
            if (now - this.lastTapTime < this.config.doubleTapDeleteMs) {
                this._removePoint(index);
                this._renderFullscreen();
                this.lastTapTime = 0;
                return;
            }
            this.lastTapTime = now;

            this.isDragging = true;
            this.dragPointIndex = index;
            group.style.cursor = 'grabbing';
            group.classList.add('dragging');
            svg.classList.add('is-dragging');
        };

        const handleMouseMove = (event) => {
            if (!this.isDragging || this.dragPointIndex === null) return;

            event.preventDefault();
            const originalSvg = this.svg;
            this.svg = this.fullscreenSvg;

            const originalConfig = { ...this.config };
            this.config.width = 800;
            this.config.height = 400;
            this.config.padding = { top: 30, right: 30, bottom: 40, left: 55 };

            const coords = this._getSvgCoords(event);
            const time = this._xToTime(coords.x);
            const intensity = this._yToIntensity(coords.y);

            this.points[this.dragPointIndex] = { time, intensity };

            this.config = originalConfig;
            this.svg = originalSvg;

            this._renderFullscreen();

            if (this.onChangeCallback) {
                this.onChangeCallback(this.points);
            }
        };

        const handleMouseUp = () => {
            if (!this.isDragging) return;

            const group = svg.querySelector(`[data-index="${this.dragPointIndex}"]`);
            if (group) {
                group.style.cursor = 'grab';
                group.classList.remove('dragging');
            }

            this.isDragging = false;
            this.dragPointIndex = null;
            svg.classList.remove('is-dragging');

            this._renderFullscreen();
            this._render(); // Also update main view

            if (this.onSaveCallback) {
                this.onSaveCallback(this.points);
            }
        };

        // Touch handlers
        const handleTouchStart = (event) => {
            const touch = event.touches[0];
            const group = document.elementFromPoint(touch.clientX, touch.clientY)?.closest('.keyframe-group');

            if (!group) {
                this.touchStartPos = { x: touch.clientX, y: touch.clientY };
                return;
            }

            event.preventDefault();
            const index = parseInt(group.dataset.index, 10);
            this.activePointerId = touch.identifier;

            this.longPressTimer = setTimeout(() => {
                this._removePoint(index);
                this._renderFullscreen();
                this.longPressTimer = null;
                this.isDragging = false;
            }, this.config.longPressDeleteMs);

            this.isDragging = true;
            this.dragPointIndex = index;
            group.classList.add('dragging');
            svg.classList.add('is-dragging');
        };

        const handleTouchMove = (event) => {
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }

            if (!this.isDragging || this.dragPointIndex === null) return;

            const touch = Array.from(event.touches).find((t) => t.identifier === this.activePointerId);
            if (!touch) return;

            event.preventDefault();
            const originalSvg = this.svg;
            this.svg = this.fullscreenSvg;

            const originalConfig = { ...this.config };
            this.config.width = 800;
            this.config.height = 400;
            this.config.padding = { top: 30, right: 30, bottom: 40, left: 55 };

            const coords = this._getSvgCoords(touch);
            const time = this._xToTime(coords.x);
            const intensity = this._yToIntensity(coords.y);

            this.points[this.dragPointIndex] = { time, intensity };

            this.config = originalConfig;
            this.svg = originalSvg;

            this._renderFullscreen();

            if (this.onChangeCallback) {
                this.onChangeCallback(this.points);
            }
        };

        const handleTouchEnd = (event) => {
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }

            if (this.touchStartPos && !this.isDragging && event.changedTouches.length > 0) {
                const touch = event.changedTouches[0];
                const dx = Math.abs(touch.clientX - this.touchStartPos.x);
                const dy = Math.abs(touch.clientY - this.touchStartPos.y);

                if (dx < 10 && dy < 10) {
                    const originalSvg = this.svg;
                    this.svg = this.fullscreenSvg;

                    const originalConfig = { ...this.config };
                    this.config.width = 800;
                    this.config.height = 400;
                    this.config.padding = { top: 30, right: 30, bottom: 40, left: 55 };

                    const coords = this._getSvgCoords(touch);
                    const { padding, width, height } = this.config;

                    if (
                        coords.x >= padding.left &&
                        coords.x <= width - padding.right &&
                        coords.y >= padding.top &&
                        coords.y <= height - padding.bottom
                    ) {
                        const time = this._xToTime(coords.x);
                        const intensity = this._yToIntensity(coords.y);

                        this.config = originalConfig;
                        this.svg = originalSvg;

                        this._addPoint(time, intensity);
                        this._renderFullscreen();
                    } else {
                        this.config = originalConfig;
                        this.svg = originalSvg;
                    }
                }
            }

            this.touchStartPos = null;

            if (!this.isDragging) return;

            const group = svg.querySelector(`[data-index="${this.dragPointIndex}"]`);
            if (group) {
                group.classList.remove('dragging');
            }

            this.isDragging = false;
            this.dragPointIndex = null;
            this.activePointerId = null;
            svg.classList.remove('is-dragging');

            this._renderFullscreen();
            this._render();

            if (this.onSaveCallback) {
                this.onSaveCallback(this.points);
            }
        };

        svg.addEventListener('click', handleClick);
        svg.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        svg.addEventListener('touchstart', handleTouchStart, { passive: false });
        document.addEventListener('touchmove', handleTouchMove, { passive: false });
        document.addEventListener('touchend', handleTouchEnd);
    }

    /**
     * Render fullscreen SVG
     */
    _renderFullscreen() {
        if (!this.fullscreenSvg) return;

        const originalSvg = this.svg;
        const originalConfig = { ...this.config };

        this.svg = this.fullscreenSvg;
        this.config.width = 800;
        this.config.height = 400;
        this.config.padding = { top: 30, right: 30, bottom: 40, left: 55 };
        this.config.keyframeRadius = 14;
        this.config.keyframeRadiusTouch = 18;

        // Get group references from fullscreen SVG
        this.gridGroup = this.fullscreenSvg.querySelector('.curve-editor-grid');
        this.fillGroup = this.fullscreenSvg.querySelector('.curve-editor-fill');
        this.curveGroup = this.fullscreenSvg.querySelector('.curve-editor-curve');
        this.pointsGroup = this.fullscreenSvg.querySelector('.curve-editor-points');
        this.labelsGroup = this.fullscreenSvg.querySelector('.curve-editor-labels');

        this._render();

        // Restore original references
        this.svg = originalSvg;
        this.config = originalConfig;
        this.gridGroup = originalSvg.querySelector('.curve-editor-grid');
        this.fillGroup = originalSvg.querySelector('.curve-editor-fill');
        this.curveGroup = originalSvg.querySelector('.curve-editor-curve');
        this.pointsGroup = originalSvg.querySelector('.curve-editor-points');
        this.labelsGroup = originalSvg.querySelector('.curve-editor-labels');
    }

    /**
     * Exit fullscreen mode
     */
    _exitFullscreen() {
        if (this.fullscreenOverlay) {
            this.fullscreenOverlay.remove();
            this.fullscreenOverlay = null;
        }

        this._unlockOrientation();
        this.isFullscreen = false;
        this.fullscreenSvg = null;
        document.body.classList.remove('curve-editor-fullscreen-active');

        // Re-render main view with updated points
        this._render();
    }

    /**
     * Try to lock screen orientation to landscape on mobile
     */
    _lockOrientation() {
        if (screen.orientation && screen.orientation.lock) {
            screen.orientation.lock('landscape').catch((e) => {
                // Orientation lock not supported or permission denied
                console.log('Could not lock orientation:', e.message);
            });
        }
    }

    /**
     * Unlock screen orientation
     */
    _unlockOrientation() {
        if (screen.orientation && screen.orientation.unlock) {
            screen.orientation.unlock();
        }
    }

    // ========================================================================
    // PUBLIC API
    // ========================================================================

    /**
     * Set curve points
     * @param {Array} points - Array of {time: "HH:MM", intensity: number}
     */
    setPoints(points) {
        this.points = points.map((p) => ({
            time: p.time,
            intensity: typeof p.intensity === 'number' ? p.intensity : parseInt(p.intensity, 10),
        }));
        this._render();
        if (this.isFullscreen) {
            this._renderFullscreen();
        }
    }

    /**
     * Get current points
     * @returns {Array} Array of {time, intensity}
     */
    getPoints() {
        return this._getSortedPoints();
    }

    /**
     * Set change callback (called during drag)
     * @param {Function} callback - (points) => void
     */
    onChange(callback) {
        this.onChangeCallback = callback;
    }

    /**
     * Set save callback (called on release)
     * @param {Function} callback - (points) => void
     */
    onSave(callback) {
        this.onSaveCallback = callback;
    }

    /**
     * Destroy the editor
     */
    destroy() {
        if (this.fullscreenOverlay) {
            this.fullscreenOverlay.remove();
        }
        this.container.innerHTML = '';
    }
}

// ============================================================================
// FACTORY FUNCTION FOR EASY INTEGRATION
// ============================================================================

/**
 * Create a curve editor for a channel
 * @param {HTMLElement|string} container - Container element or selector
 * @param {number} channel - Channel number (1-4)
 * @param {Array} initialPoints - Initial curve points
 * @param {Object} options - Configuration options
 * @returns {BezierCurveEditor} Editor instance
 */
export function createCurveEditor(container, channel, initialPoints = [], options = {}) {
    const containerEl = typeof container === 'string' ? document.querySelector(container) : container;

    if (!containerEl) {
        console.error('Curve editor container not found:', container);
        return null;
    }

    const editor = new BezierCurveEditor(containerEl, channel, options);
    editor.setPoints(initialPoints);

    return editor;
}
