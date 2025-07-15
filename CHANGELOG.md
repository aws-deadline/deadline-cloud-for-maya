## 0.15.8 (2025-07-15)


### Features
* add support for auto-populating maya-vray conda package in submitter (#289) ([`26063d8`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/26063d8f6f730a69bff26cd33b3356d00869f6e9))


## 0.15.7 (2025-07-03)


### Features
* add maya-redshift to conda-package auto-populate  (#297) ([`de8adbd`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/de8adbd689bb7fdef6d29b01bfe02dd42cd97b3b))
* add validation for frame range field in submitter ui (#295) ([`5467cbf`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/5467cbf87456ea712d8a9ec65fe5930913bf2625))


## 0.15.6 (2025-06-25)



### Bug Fixes
* Maya scene with many asset files hangs without user feedback (#287) ([`4b69f6b`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/4b69f6bfa8eb93e5fd4d8ac44917234cea517e1b))

## 0.15.5 (2025-06-05)


### Features
* Add ignore version enviroment variable flag (#280) ([`17391a9`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/17391a9a1b181f11fe22b90698e72da5dab3d333))
* Update Maya adaptor to support Redshift renderer via redshift4maya plugin (#277) ([`f6667bf`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/f6667bf8714a225e30fe3b5b2a1fe042accefbff))
* allow adaptor to ignore version when open scene (#273) ([`a1361ef`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/a1361efd568bc4c6a8f8e4f92cc6eae7b2c9346e))

### Bug Fixes
* sdist failed to install (#281) ([`0bb9847`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/0bb9847eab28d82a547a0b8171055324b848e579))
* Fix submitter integration test for Windows (#278) ([`c7bdb58`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/c7bdb585d9de02667ec924fed6e8c2f7ea26b598))
* fixed Maya submitter to pull the correct image resolution from scene ([`20c3a72`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/20c3a72cd711715e61bb02255ddaa78df212d893))

## 0.15.4 (2025-04-16)



### Bug Fixes
* move mod file to a user folder to prevent permission issue (#269) ([`615b21a`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/615b21a9ab8020adc4dcaea4b752eddc10898c85))

## 0.15.3 (2025-04-14)


### Features
* Add standalone installer for Maya Submitter (#255) ([`3c124fe`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/3c124fe844e5a77b0dda16f0b1b73f60edbf9cf5))

### Bug Fixes
* Arnold licensing error handling for mtoa5.4.7.1 (#252) ([`9c39e47`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/9c39e4761f4e1d82b82f56a3f2ba73dbdc8525fa))

## 0.15.2 (2025-03-06)

### Bug Fixes
* Changed the cameras dropdown wording option from "All Cameras" to "All Renderable Cameras" in the submitter ([`a6d983c`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/a6d983c76f2628d827693c78baa4ee78a2bb0c0d))
* Tighten error regex pattern for Maya Adaptor. ([`67bbc97`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/67bbc970dbc6c6e4273127d8ecf7ae310735f4b9))
* Use `byFrameStep` instead of `byFrame` (#224) ([`677137d`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/677137d6a67e18d1a787671dd134096a8df0b04a))
* Update the warning message used when the scene has unsaved changes (#238) ([`c9b5e74`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/c9b5e7479e21c76184ba522e3cd983dd8b35a647))
* OutputPath is read from the scene in the submitter (#231) ([`d77f474`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/d77f47491372abec3324410e0cd2eb7cbc68a7eb))
* Load scene settings when the submitter is open (#229) ([`94ee920`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/94ee920f7a0707c5308a26fb33571c85c1af7555))

## 0.15.1 (2025-02-03)

* This release only includes documentation updates (#227) ([`e0a3827`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/e0a38272e6cab7dac27f0af8c7c64ce3a79189ae))


## 0.15.0 (2025-01-09)

### BREAKING CHANGES
* Allow specifying MAYAPY exe via environment (#200) ([`29634ca`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/29634ca1bbf070cbd9311329204ce09601e9a0b9))


### Bug Fixes
* **submitter**: read includeAllLights setting correctly (#207) ([`f5d0435`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/f5d0435d0548488622972324c9d5804d63f7aa8d))
* fix README typos (#203) ([`d0594a8`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/d0594a8ca3dad6689691a7151a14a98aaa773b76))

## 0.14.4 (2024-11-19)


### Features
* add Maya 2025 submitter support (#183) ([`a4fc035`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/a4fc035ae96ceb8c97e11dad5db93bd896633e85))

### Bug Fixes
* maya 2025 submitter failed to load due to qt setMargin being removed (#192) ([`39ca5fc`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/39ca5fcec28d5d5c8cb0f5d05192c6043d528694))
* frame override does not enable frame list in Maya 2025 (#190) ([`b054dd4`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/b054dd46a7f7ebc1f025798aa323d122d843f413))
* include description in job submission (#188) ([`c279cfd`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/c279cfd7cce0b67b84af6c9e83847733cfb1dbb8))

## 0.14.3 (2024-10-17)


### Features
* Add the ability to specify a render region ([`419a06b`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/419a06b73b1b4914561e36e97c95a5e325c61762))

### Bug Fixes
* import HTTPClientInterface correctly on Windows (#184) ([`1208134`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/1208134b63d215b21ee86a4682ebc686079d3a21))

## 0.14.2 (2024-08-22)



### Bug Fixes
* when listing layers make sure referenced layers are active. (#164) ([`bf16897`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/bf16897360018100e5ad5bb4b12781d9d72682c3))
* adaptor wheel override (#162) ([`4ef10ce`](https://github.com/aws-deadline/deadline-cloud-for-maya/commit/4ef10ce306d231a6dc927165df5e70e1649338c6))

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

