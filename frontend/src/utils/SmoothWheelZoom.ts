import L from 'leaflet';

interface ISmoothWheelZoom {
  _map: L.Map;
  _isWheeling: boolean;
  _wheelMousePosition: L.Point;
  _centerPoint: L.Point;
  _startLatLng: L.LatLng;
  _wheelMouseLatLng: L.LatLng;
  _startZoom: number;
  _moved: boolean;
  _zooming: boolean;
  _goalZoom: number;
  _prevCenter: L.LatLng;
  _prevZoom: number;
  _zoomAnimationId: number;
  _timeoutId: ReturnType<typeof setTimeout>;
  _zoom: number;
  _center: L.LatLng;
  // Bound once in addHooks to avoid a fresh closure on every rAF tick
  _boundUpdateWheelZoom: FrameRequestCallback;
  _boundOnWheelEnd: () => void;
  _onWheelScroll(e: Event): void;
  _onWheelStart(e: Event): void;
  _onWheeling(e: Event): void;
  _onWheelEnd(): void;
  _updateWheelZoom(): void;
}

export function initSmoothWheelZoom() {
  if ((L.Map as any).SmoothWheelZoom) return;

  L.Map.mergeOptions({
      smoothWheelZoom: true,
      smoothSensitivity: 1
  });

  (L.Map as any).SmoothWheelZoom = L.Handler.extend({
      addHooks: function (this: ISmoothWheelZoom) {
          // Bind once here so the same function reference is used for add/remove
          // and we don't create a fresh closure on every rAF tick.
          this._boundUpdateWheelZoom = this._updateWheelZoom.bind(this);
          this._boundOnWheelEnd = this._onWheelEnd.bind(this);
          L.DomEvent.on(this._map._container, 'wheel', this._onWheelScroll, this);
      },
      removeHooks: function (this: ISmoothWheelZoom) {
          L.DomEvent.off(this._map._container, 'wheel', this._onWheelScroll, this);
          cancelAnimationFrame(this._zoomAnimationId);
          clearTimeout(this._timeoutId);
      },
      _onWheelScroll: function (this: ISmoothWheelZoom, e: Event) {
          if (!this._isWheeling) {
              this._onWheelStart(e);
          }
          this._onWheeling(e);
      },
      _onWheelStart: function (this: ISmoothWheelZoom, e: Event) {
          const map = this._map;
          const wheelEvent = e as WheelEvent;
          this._isWheeling = true;
          this._wheelMousePosition = map.mouseEventToContainerPoint(wheelEvent);
          this._centerPoint = map.getSize().divideBy(2);
          this._startLatLng = map.containerPointToLatLng(this._centerPoint);
          this._wheelMouseLatLng = map.containerPointToLatLng(this._wheelMousePosition);
          this._startZoom = map.getZoom();
          this._moved = false;
          this._zooming = true;

          map._stop();
          if (map._panAnim) map._panAnim.stop();

          this._goalZoom = map.getZoom();
          this._prevCenter = map.getCenter();
          this._prevZoom = map.getZoom();

          this._zoomAnimationId = requestAnimationFrame(this._boundUpdateWheelZoom);
      },
      _onWheeling: function (this: ISmoothWheelZoom, e: Event) {
          const map = this._map;
          const wheelEvent = e as WheelEvent;

          this._goalZoom = this._goalZoom + L.DomEvent.getWheelDelta(wheelEvent) * 0.003 * (map.options.smoothSensitivity || 1);
          if (this._goalZoom < map.getMinZoom() || this._goalZoom > map.getMaxZoom()) {
              this._goalZoom = map._limitZoom(this._goalZoom);
          }
          this._wheelMousePosition = this._map.mouseEventToContainerPoint(wheelEvent);
          this._wheelMouseLatLng = map.containerPointToLatLng(this._wheelMousePosition);

          clearTimeout(this._timeoutId);
          this._timeoutId = setTimeout(this._boundOnWheelEnd, 200);

          L.DomEvent.preventDefault(e);
          L.DomEvent.stopPropagation(e);
      },
      _onWheelEnd: function (this: ISmoothWheelZoom) {
          this._isWheeling = false;
          cancelAnimationFrame(this._zoomAnimationId);
          this._map._moveEnd(true);
      },
      _updateWheelZoom: function (this: ISmoothWheelZoom) {
          const map = this._map;

          if ((!map.getCenter().equals(this._prevCenter)) || map.getZoom() != this._prevZoom)
              return;

          this._zoom = map.getZoom() + (this._goalZoom - map.getZoom()) * 0.3;

          const delta = this._wheelMousePosition.subtract(this._centerPoint);
          if (delta.x === 0 && delta.y === 0)
              return;

          if (map.options.smoothWheelZoom === 'center') {
              this._center = this._startLatLng;
          } else {
              this._center = map.unproject(map.project(this._wheelMouseLatLng, this._zoom).subtract(delta), this._zoom);
          }

          if (!this._moved) {
              map._moveStart(true, false);
              this._moved = true;
          }

          map._move(this._center, this._zoom);
          this._prevCenter = map.getCenter();
          this._prevZoom = map.getZoom();

          this._zoomAnimationId = requestAnimationFrame(this._boundUpdateWheelZoom);
      }
  });

  L.Map.addInitHook('addHandler', 'smoothWheelZoom', (L.Map as any).SmoothWheelZoom);
}
