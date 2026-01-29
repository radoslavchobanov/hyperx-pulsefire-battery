# Maintainer: Radoslav Chobanov <rado.chobanov97@gmail.com>
# HyperX Pulsefire Dart Configuration Tool - NGenuity replacement for Linux
#
# Build from local source:
#   makepkg -si
#
# Build from Git:
#   Uncomment the git source below and comment out the local source

pkgname=hyperx-pulsefire-battery
pkgver=2.0.0
pkgrel=1
pkgdesc="Full configuration tool and battery monitor for HyperX Pulsefire Dart wireless mouse on Linux - NGenuity replacement"
arch=('any')
url="https://github.com/radoslavchobanov/hyperx-pulsefire-battery"
license=('MIT')
depends=(
    'python>=3.8'
    'python-hidapi'
    'python-pyqt5'
    'python-pyudev'
)
makedepends=(
    'python-build'
    'python-installer'
    'python-wheel'
    'python-setuptools'
)
backup=('etc/udev/rules.d/99-hyperx-pulsefire.rules')
install=hyperx-pulsefire-battery.install

# For local builds (run makepkg in the repo directory)
source=()
sha256sums=()

# For release builds, uncomment:
# source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
# sha256sums=('SKIP')

build() {
    cd "${startdir}"
    python -m build --wheel --no-isolation
}

package() {
    cd "${startdir}"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Install udev rules
    install -Dm644 99-hyperx-pulsefire.rules "$pkgdir/usr/lib/udev/rules.d/99-hyperx-pulsefire.rules"

    # Install desktop file for autostart
    install -Dm644 hyperx-battery-tray.desktop "$pkgdir/usr/share/applications/hyperx-battery-tray.desktop"

    # Install autostart entry
    install -Dm644 hyperx-battery-tray.desktop "$pkgdir/etc/xdg/autostart/hyperx-battery-tray.desktop"

    # Install license
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"

    # Install documentation
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
    install -Dm644 CHANGELOG.md "$pkgdir/usr/share/doc/$pkgname/CHANGELOG.md"
}
