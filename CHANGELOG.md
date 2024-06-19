## 0.14.2 (2024-06-19)




## 0.14.1 (2024-05-01)

### Dependencies
* Update deadline requirement from ==0.47.* to ==0.48.* (#149) ([`2de6f48`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/2de6f48bc8eb57c85e14515af04528e5f0715485))


## 0.14.0 (2024-04-01)

### BREAKING CHANGES
* publish release (#132) ([`cee87da`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/cee87dafd1af6afe3e076d9bf9f764df7f1f1e11))
* set python 3.8 to minimum python version in hatch testing matrix (#132) ([`cee87da`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/cee87dafd1af6afe3e076d9bf9f764df7f1f1e11))


### Bug Fixes
* catch import errors, link to libssl issue (#134) ([`af79694`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/af79694799661ee9abbaae50c8e4d32981b3dda8))
* include deps with openjd adaptor package (#129) ([`bb6882e`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/bb6882e83a8607245cf43fc1487b5182a941823c))
* incorrect package name in create adaptor script (#128) ([`c616bf7`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/c616bf7edb0d14a1f16eec2d79486115831eaf2d))
* include the adaptor deps in the package (#127) ([`d926ecf`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/d926ecf5911600e85f99964779c23e0e72135bd9))

## 0.13.2 (2024-03-26)


### Features
* Add telemetry data to submitter and adaptor (#114) ([`d853496`](https://github.com/casillas2/deadline-cloud-for-maya/commit/d853496ce18659ef4cd041e8662274a57d0c2c40))

### Bug Fixes
* include deadline-cloud in the adaptor packaging script (#125) ([`fdd491d`](https://github.com/casillas2/deadline-cloud-for-maya/commit/fdd491dcadabf03edef9ed2e01ed9ad81b4f9227))

## 0.13.1 (2024-03-15)


### Features
* add Renderman Handler (#98) ([`bca84a2`](https://github.com/casillas2/deadline-cloud-for-maya/commit/bca84a2afc92188e01d6556dc0bd54ed114268d3))

### Chores
* update deps deadline-cloud 0.40 (#116) ([`4d4da99`](https://github.com/casillas2/deadline-cloud-for-maya/commit/4d4da996352d66f5e53eb1a71cf78103811e9cc8))

## 0.13.0 (2024-03-08)

### BREAKING CHANGES
* **deps**: update openjd-adaptor-runtime to 0.5 (#108) ([`cc119f6`](https://github.com/casillas2/deadline-cloud-for-maya/commit/cc119f659294fb5440474ea579b14231a5d031f7))

### Features
* Adding Yeti support (#101) ([`cffda91`](https://github.com/casillas2/deadline-cloud-for-maya/commit/cffda91211b7e2b6b72c7ba607c40e8929b56eef))

### Bug Fixes
* properly fill out allowed values for camera job parameter (#103) ([`3c2d42f`](https://github.com/casillas2/deadline-cloud-for-maya/commit/3c2d42f102025ec9c06f7b0f64fb29941e31aed7))

## 0.12.0 (2024-02-21)

### BREAKING CHANGES
* Create a script to build adaptor packaging artifacts (#87) ([`45be338`](https://github.com/casillas2/deadline-cloud-for-maya/commit/45be3384b08d195f33f64f1f4c98df8fac78239e))

### Features
* Add support for renderman job attachments. (#86) ([`fcef5f2`](https://github.com/casillas2/deadline-cloud-for-maya/commit/fcef5f2894ac4d814fa596ebb05bfb409cd6102c))

### Bug Fixes
* use right mode when opening toml file (#90) ([`62a136b`](https://github.com/casillas2/deadline-cloud-for-maya/commit/62a136b2c33a6c0e895155cb954ffd9460f40bea))
* libtoml -&gt; tomllib in depsBundle.py (#89) ([`a477805`](https://github.com/casillas2/deadline-cloud-for-maya/commit/a477805da6bf851d8fd12b46ac149234e85223d7))
* **dev**: add executable bit to build_wheels.sh (#82) ([`1a4fe71`](https://github.com/casillas2/deadline-cloud-for-maya/commit/1a4fe71b3fa6ccac2bc1846eae9efcadc8dd2d52))

