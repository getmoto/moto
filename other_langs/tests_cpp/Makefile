build:
	pwd
	ls -la
	mkdir -p build/vcpkg
	git clone https://github.com/microsoft/vcpkg.git build/vcpkg
	ls -la build
	ls -la build/vcpkg
	./build/vcpkg/bootstrap-vcpkg.sh --disableMetrics
	./build/vcpkg/vcpkg install "aws-sdk-cpp[s3]" --recurse
	cmake -S . -B build/ -DCMAKE_TOOLCHAIN_FILE=build/vcpkg/scripts/buildsystems/vcpkg.cmake
	cmake --build build

test:
	./build/hello_s3
