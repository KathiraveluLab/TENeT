/*
 * Adapted from Leaflet.SmoothWheelZoom.
 * Copyright (c) 2018 mutsuyuki
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
import L from 'leaflet';

const TRACKPAD_PINCH_MULTIPLIER = 4;

type SmoothWheelMap = L.Map & {
  _limitZoom: (zoom: number) => number;
  _move: (
    center: L.LatLng,
    zoom: number,
    data?: { pinch?: boolean; round?: boolean },
    suppressEvent?: boolean,
  ) => L.Map;
  _moveEnd: (zoomChanged: boolean) => L.Map;
  _moveStart: (zoomChanged: boolean, noMoveStart: boolean) => L.Map;
  _stop: () => L.Map;
};

class SmoothWheelZoom extends L.Handler {
  private readonly map: SmoothWheelMap;
  private animationFrame: number | null = null;
  private wheelEndTimer: ReturnType<typeof window.setTimeout> | null = null;
  private isWheeling = false;
  private moved = false;
  private goalZoom = 0;
  private previousZoom = 0;
  private previousCenter?: L.LatLng;
  private wheelMousePosition?: L.Point;
  private wheelMouseLatLng?: L.LatLng;
  private centerPoint?: L.Point;
  private startLatLng?: L.LatLng;

  constructor(map: L.Map) {
    super(map);
    this.map = map as SmoothWheelMap;
  }

  addHooks(): void {
    L.DomEvent.on(this.map.getContainer(), 'wheel', this.onWheelScroll, this);
  }

  removeHooks(): void {
    L.DomEvent.off(this.map.getContainer(), 'wheel', this.onWheelScroll, this);
    this.finishWheel();
  }

  private onWheelScroll(event: Event): void {
    L.DomEvent.preventDefault(event);
    L.DomEvent.stopPropagation(event);

    const wheelEvent = event as WheelEvent;
    if (!this.isWheeling) {
      this.startWheel(wheelEvent);
    }

    this.updateWheelGoal(wheelEvent);
  }

  private startWheel(event: WheelEvent): void {
    this.isWheeling = true;
    this.wheelMousePosition = this.map.mouseEventToContainerPoint(event);
    this.centerPoint = this.map.getSize().divideBy(2);
    this.startLatLng = this.map.containerPointToLatLng(this.centerPoint);
    this.wheelMouseLatLng = this.map.containerPointToLatLng(this.wheelMousePosition);
    this.moved = false;

    this.map._stop();
    this.goalZoom = this.map.getZoom();
    this.previousCenter = this.map.getCenter();
    this.previousZoom = this.map.getZoom();
    this.animationFrame = window.requestAnimationFrame(this.animateZoom);
  }

  private updateWheelGoal(event: WheelEvent): void {
    const sensitivity = this.map.options.smoothSensitivity ?? 1;
    const gestureMultiplier = event.ctrlKey ? TRACKPAD_PINCH_MULTIPLIER : 1;
    this.goalZoom += L.DomEvent.getWheelDelta(event) * 0.003
      * sensitivity * gestureMultiplier;

    if (this.goalZoom < this.map.getMinZoom() || this.goalZoom > this.map.getMaxZoom()) {
      this.goalZoom = this.map._limitZoom(this.goalZoom);
    }

    this.wheelMousePosition = this.map.mouseEventToContainerPoint(event);

    if (this.wheelEndTimer !== null) {
      window.clearTimeout(this.wheelEndTimer);
    }
    this.wheelEndTimer = window.setTimeout(() => this.finishWheel(), 200);
  }

  private finishWheel(): void {
    if (this.wheelEndTimer !== null) {
      window.clearTimeout(this.wheelEndTimer);
      this.wheelEndTimer = null;
    }

    if (this.animationFrame !== null) {
      window.cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }

    if (!this.isWheeling) return;

    this.isWheeling = false;
    if (this.moved) {
      this.map.fire('zoom');
      this.map._moveEnd(true);
    }
  }

  private animateZoom = (): void => {
    if (
      !this.isWheeling
      || !this.previousCenter
      || !this.wheelMousePosition
      || !this.wheelMouseLatLng
      || !this.centerPoint
      || !this.startLatLng
      || !this.map.getCenter().equals(this.previousCenter)
      || this.map.getZoom() !== this.previousZoom
    ) {
      return;
    }

    const zoom = this.map.getZoom() + (this.goalZoom - this.map.getZoom()) * 0.3;
    const delta = this.wheelMousePosition.subtract(this.centerPoint);
    let center: L.LatLng;

    if (this.map.options.smoothWheelZoom === 'center') {
      center = this.startLatLng;
    } else {
      center = this.map.unproject(
        this.map.project(this.wheelMouseLatLng, zoom).subtract(delta),
        zoom,
      );
    }

    if (!this.moved) {
      this.map._moveStart(true, false);
      this.moved = true;
    }

    this.map.fire('zoomanim', { center, zoom, noUpdate: true });
    this.map._move(center, zoom, undefined, true);
    this.previousCenter = this.map.getCenter();
    this.previousZoom = this.map.getZoom();
    this.animationFrame = window.requestAnimationFrame(this.animateZoom);
  };
}

L.Map.addInitHook('addHandler', 'smoothWheelZoom', SmoothWheelZoom);
