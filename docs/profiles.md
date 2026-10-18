# Native profile reference

Generated from the executed runtime catalog; not a native-fixture verification claim.

| Profile | Required native stages | Project commands required |
|---|---|---|
| `python` | setup, toolchain, format, lint, type, test, build, consumer | Native defaults |
| `rust` | toolchain, format, lint, test, doctest, build, policy | Native defaults |
| `go` | toolchain, format, lint, dependencies, test, build, package | Native defaults |
| `typescript-javascript` | setup, toolchain, format, lint, type, test, build, package | Native defaults |
| `c-cpp` | configure, format, lint, build, test, package | format, lint |
| `qt` | toolchain, configure, build, test, package | Native defaults |
| `dart-flutter` | setup, toolchain, lint, test, generate, build | generate, build |
| `jvm` | toolchain, dependencies, lint, test, build | dependencies, lint |
| `android-kotlin` | toolchain, dependencies, lint, test, build | Native defaults |
| `dotnet` | toolchain, setup, format, build, test, package | Native defaults |
| `swift` | toolchain, dependencies, lint, test, build, package | lint |
| `php` | toolchain, setup, locks, lint, type, test, package | Native defaults |
| `ruby` | toolchain, setup, lint, test, build | Native defaults |
| `r` | toolchain, setup, lint, test, build, package | package |
| `sql-data` | lint, empty-migration, previous-migration, test | empty-migration, previous-migration, test |
| `shell-powershell` | syntax, lint, test | syntax, lint, test |
| `documentation` | syntax, external-links, generate, examples | external-links, generate, examples |
| `workflows` | lint, security, contracts | Native defaults |
| `container` | lint, build, test, scan, sbom | build, test, scan, sbom |
| `infrastructure` | format, validate, security, generate | format, validate, security, generate |
| `security` | secrets, dependencies, sast, licenses | sast, licenses |
| `architecture` | scope, dependencies | dependencies |
| `advanced-testing` | bounded-operation, result | bounded-operation, result |

Commands can be overridden through the caller contract; selected baseline stages remain required.

## Native defaults

```json
{
  "python": {
    "manifests": [
      "pyproject.toml"
    ],
    "stages": {
      "setup": [
        "uv",
        "sync",
        "--locked"
      ],
      "toolchain": [
        "uv",
        "run",
        "python",
        "--version"
      ],
      "format": [
        "uv",
        "run",
        "ruff",
        "format",
        "--check",
        "."
      ],
      "lint": [
        "uv",
        "run",
        "ruff",
        "check",
        "."
      ],
      "type": [
        "uv",
        "run",
        "basedpyright"
      ],
      "test": [
        "uv",
        "run",
        "pytest",
        "--junitxml=.nddev-reports/pytest.xml",
        "--cov",
        "--cov-report=xml:.nddev-reports/coverage.xml"
      ],
      "build": [
        "uv",
        "build"
      ],
      "consumer": [
        "@library",
        "package-check"
      ]
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/pytest.xml"
    }
  },
  "rust": {
    "manifests": [
      "Cargo.toml"
    ],
    "stages": {
      "toolchain": [
        "rustc",
        "--version"
      ],
      "format": [
        "cargo",
        "fmt",
        "--all",
        "--check"
      ],
      "lint": [
        "cargo",
        "clippy",
        "--locked",
        "--all-targets",
        "--",
        "-D",
        "warnings"
      ],
      "test": [
        "cargo",
        "test",
        "--locked",
        "--all-targets"
      ],
      "doctest": [
        "cargo",
        "test",
        "--locked",
        "--doc"
      ],
      "build": [
        "cargo",
        "package",
        "--locked"
      ],
      "policy": [
        "cargo",
        "deny",
        "check"
      ]
    },
    "report": {
      "kind": "cargo"
    }
  },
  "go": {
    "manifests": [
      "go.mod"
    ],
    "stages": {
      "toolchain": [
        "go",
        "version"
      ],
      "format": "test -z \"$(gofmt -l .)\"",
      "lint": [
        "go",
        "vet",
        "./..."
      ],
      "dependencies": [
        "go",
        "mod",
        "verify"
      ],
      "test": [
        "go",
        "test",
        "-json",
        "-coverprofile=.nddev-reports/go.cover",
        "./..."
      ],
      "build": [
        "go",
        "build",
        "./..."
      ],
      "package": [
        "go",
        "list",
        "-m",
        "-json",
        "all"
      ]
    },
    "report": {
      "kind": "go-json"
    }
  },
  "typescript-javascript": {
    "manifests": [
      "package.json"
    ],
    "stages": {
      "setup": [
        "npm",
        "ci"
      ],
      "toolchain": [
        "node",
        "--version"
      ],
      "format": [
        "npm",
        "run",
        "format:check"
      ],
      "lint": [
        "npm",
        "run",
        "lint"
      ],
      "type": [
        "npm",
        "run",
        "typecheck"
      ],
      "test": [
        "npm",
        "run",
        "test:ci"
      ],
      "build": [
        "npm",
        "run",
        "build"
      ],
      "package": [
        "npm",
        "pack",
        "--dry-run"
      ]
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "c-cpp": {
    "manifests": [
      "CMakeLists.txt",
      "meson.build",
      "Makefile"
    ],
    "stages": {
      "configure": [
        "cmake",
        "-S",
        ".",
        "-B",
        "build",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
      ],
      "format": null,
      "lint": null,
      "build": [
        "cmake",
        "--build",
        "build",
        "--parallel",
        "2"
      ],
      "test": [
        "ctest",
        "--test-dir",
        "build",
        "--output-on-failure",
        "--no-tests=error",
        "--output-junit",
        "../.nddev-reports/ctest.xml"
      ],
      "package": [
        "cpack",
        "--config",
        "build/CPackConfig.cmake"
      ]
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "qt": {
    "manifests": [
      "CMakeLists.txt",
      "*.pro"
    ],
    "stages": {
      "toolchain": [
        "qtpaths",
        "--qt-version"
      ],
      "configure": [
        "cmake",
        "-S",
        ".",
        "-B",
        "build"
      ],
      "build": [
        "cmake",
        "--build",
        "build",
        "--parallel",
        "2"
      ],
      "test": [
        "ctest",
        "--test-dir",
        "build",
        "--output-on-failure",
        "--no-tests=error",
        "--output-junit",
        "../.nddev-reports/qt.xml"
      ],
      "package": [
        "cpack",
        "--config",
        "build/CPackConfig.cmake"
      ]
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "dart-flutter": {
    "manifests": [
      "pubspec.yaml"
    ],
    "stages": {
      "setup": [
        "flutter",
        "pub",
        "get",
        "--enforce-lockfile"
      ],
      "toolchain": [
        "flutter",
        "--version"
      ],
      "lint": [
        "flutter",
        "analyze",
        "--fatal-infos"
      ],
      "test": [
        "flutter",
        "test",
        "--machine"
      ],
      "generate": null,
      "build": null
    },
    "report": {
      "kind": "dart-json"
    }
  },
  "jvm": {
    "manifests": [
      "pom.xml",
      "build.gradle",
      "build.gradle.kts"
    ],
    "stages": {
      "toolchain": [
        "java",
        "-version"
      ],
      "dependencies": null,
      "lint": null,
      "test": [
        "./mvnw",
        "--batch-mode",
        "verify"
      ],
      "build": [
        "./mvnw",
        "--batch-mode",
        "package",
        "-DskipTests"
      ]
    },
    "report": {
      "kind": "junit",
      "path": "target/surefire-reports/*.xml"
    }
  },
  "android-kotlin": {
    "manifests": [
      "build.gradle",
      "build.gradle.kts"
    ],
    "stages": {
      "toolchain": [
        "java",
        "-version"
      ],
      "dependencies": [
        "./gradlew",
        "--dependency-verification=strict",
        "dependencies"
      ],
      "lint": [
        "./gradlew",
        "lint"
      ],
      "test": [
        "./gradlew",
        "testDebugUnitTest"
      ],
      "build": [
        "./gradlew",
        "assembleDebug"
      ]
    },
    "report": {
      "kind": "junit",
      "path": "**/build/test-results/**/*.xml"
    }
  },
  "dotnet": {
    "manifests": [
      "*.sln",
      "*.slnx",
      "*.csproj"
    ],
    "stages": {
      "toolchain": [
        "dotnet",
        "--info"
      ],
      "setup": [
        "dotnet",
        "restore",
        "--locked-mode"
      ],
      "format": [
        "dotnet",
        "format",
        "--verify-no-changes",
        "--no-restore"
      ],
      "build": [
        "dotnet",
        "build",
        "--no-restore"
      ],
      "test": [
        "dotnet",
        "test",
        "--no-build",
        "--logger",
        "trx",
        "--results-directory",
        ".nddev-reports",
        "--collect:XPlat Code Coverage"
      ],
      "package": [
        "dotnet",
        "pack",
        "--no-build"
      ]
    },
    "report": {
      "kind": "trx",
      "path": ".nddev-reports/*.trx"
    }
  },
  "swift": {
    "manifests": [
      "Package.swift",
      "*.xcodeproj"
    ],
    "stages": {
      "toolchain": [
        "swift",
        "--version"
      ],
      "dependencies": [
        "swift",
        "package",
        "resolve",
        "--only-use-versions-from-resolved-file"
      ],
      "lint": null,
      "test": [
        "swift",
        "test",
        "--parallel",
        "--xunit-output",
        ".nddev-reports/swift.xml"
      ],
      "build": [
        "swift",
        "build",
        "-c",
        "release"
      ],
      "package": [
        "swift",
        "package",
        "describe",
        "--type",
        "json"
      ]
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "php": {
    "manifests": [
      "composer.json"
    ],
    "stages": {
      "toolchain": [
        "php",
        "--version"
      ],
      "setup": [
        "composer",
        "install",
        "--no-interaction",
        "--prefer-dist"
      ],
      "locks": [
        "composer",
        "validate",
        "--strict"
      ],
      "lint": [
        "composer",
        "run",
        "lint"
      ],
      "type": [
        "composer",
        "run",
        "analyse"
      ],
      "test": [
        "vendor/bin/phpunit",
        "--log-junit",
        ".nddev-reports/phpunit.xml"
      ],
      "package": [
        "composer",
        "archive",
        "--format=zip"
      ]
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "ruby": {
    "manifests": [
      "Gemfile"
    ],
    "stages": {
      "toolchain": [
        "ruby",
        "--version"
      ],
      "setup": [
        "bundle",
        "install"
      ],
      "lint": [
        "bundle",
        "exec",
        "rubocop"
      ],
      "test": [
        "bundle",
        "exec",
        "rspec",
        "--format",
        "RspecJunitFormatter",
        "--out",
        ".nddev-reports/rspec.xml"
      ],
      "build": "gem build *.gemspec"
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "r": {
    "manifests": [
      "DESCRIPTION",
      "renv.lock"
    ],
    "stages": {
      "toolchain": [
        "R",
        "--version"
      ],
      "setup": [
        "Rscript",
        "-e",
        "renv::restore(prompt=FALSE)"
      ],
      "lint": [
        "Rscript",
        "-e",
        "stopifnot(length(lintr::lint_package()) == 0)"
      ],
      "test": [
        "Rscript",
        "-e",
        "testthat::test_local(reporter=testthat::JunitReporter$new(file=\".nddev-reports/testthat.xml\"))"
      ],
      "build": [
        "R",
        "CMD",
        "build",
        "."
      ],
      "package": null
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "sql-data": {
    "manifests": [
      "*.sql",
      "migrations/*.sql"
    ],
    "stages": {
      "lint": [
        "sqlfluff",
        "lint",
        "."
      ],
      "empty-migration": null,
      "previous-migration": null,
      "test": null
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "shell-powershell": {
    "manifests": [
      "*.sh",
      "*.ps1",
      "scripts/*.sh",
      "scripts/*.ps1"
    ],
    "stages": {
      "syntax": null,
      "lint": null,
      "test": null
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "documentation": {
    "manifests": [],
    "stages": {
      "syntax": [],
      "external-links": null,
      "generate": null,
      "examples": null
    }
  },
  "workflows": {
    "manifests": [
      ".github/workflows/*.yml",
      ".github/workflows/*.yaml"
    ],
    "stages": {
      "lint": [
        "actionlint"
      ],
      "security": [
        "zizmor",
        "--offline",
        "--no-progress",
        ".github"
      ],
      "contracts": [
        "@library",
        "workflow-check"
      ]
    }
  },
  "container": {
    "manifests": [
      "Dockerfile",
      "**/Dockerfile"
    ],
    "stages": {
      "lint": [
        "hadolint",
        "Dockerfile"
      ],
      "build": null,
      "test": null,
      "scan": null,
      "sbom": null
    },
    "report": {
      "kind": "junit",
      "path": ".nddev-reports/*.xml"
    }
  },
  "infrastructure": {
    "manifests": [
      "*.tf",
      "*.yaml",
      "*.yml",
      "**/*.yaml"
    ],
    "stages": {
      "format": null,
      "validate": null,
      "security": null,
      "generate": null
    }
  },
  "security": {
    "manifests": [],
    "stages": {
      "secrets": [
        "gitleaks",
        "git",
        "--redact",
        "--no-banner"
      ],
      "dependencies": [
        "osv-scanner",
        "scan",
        "source",
        "--recursive",
        "."
      ],
      "sast": null,
      "licenses": null
    }
  },
  "architecture": {
    "manifests": [],
    "stages": {
      "scope": [],
      "dependencies": null
    }
  },
  "advanced-testing": {
    "manifests": [],
    "stages": {
      "bounded-operation": null,
      "result": null
    }
  }
}
```
