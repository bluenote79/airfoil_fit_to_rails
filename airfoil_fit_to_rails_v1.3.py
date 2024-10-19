"""
This skript imports airfoils to fusion 360 fits them to rails for lofting. The trailing edge can be opened for a gap by rotating the top and bottom around the nose.
author: bluenote79

"""

import adsk.core, adsk.fusion, adsk.cam, traceback
import re
import os
import os.path
import math

COMMAND_ID = "Airfoil"
B1_BUTTON_ID = "DAT Datei"
B1_BUTTON_NAME = "DAT Datei"
SE01_SELECTION_INPUT_ID = "Schiene Nasenleiste"
SE02_SELECTION_INPUT_ID = "Schiene Endleiste"
SE04_SELECTION_INPUT_ID = "Projektionsebene"
I0_VALUE_ID = "Endleistendicke"
I0_VALUE_NAME = "Endleistendicke"
C0_CHECKBOX_ID = "spiegeln"
D1_DROPDOWN_ID = "horizontale Axe"
D1_DROPDOWN_NAME = "horizontale Axe"
D2_DROPDOWN_ID = "vertikale Axe"
D2_DROPDOWN_NAME = "vertikale Axe"
C1_CHECKBOX_ID = "Profil an der Nasenleiste trennen"
C2_CHECKBOX_ID = "Tangentenhantel vertikal"
I1_VALUE_ID = "Faktor Profilaufdickung"
I1_VALUE_NAME = "Faktor Profilaufdickung"
I2_VALUE_ID = "Anzahl Interpolationspunkte"
I2_VALUE_NAME = "Anzahl Interpolationspunkte"


_handlers = []
_user_parameters = {}

global airfoildata, top_coords, bottom_coords, name

ui = None
app = adsk.core.Application.get()
if app:
    ui = app.userInterface

product = app.activeProduct
design = adsk.fusion.Design.cast(product)
root = design.rootComponent
sketches = root.sketches
planes = root.constructionPlanes


class FoilCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):

        global airfoildata, top_coords, bottom_coords, name

        try:
            eventArgs = adsk.core.InputChangedEventArgs.cast(args)
            inputs = eventArgs.inputs
            cmdInput = eventArgs.input

            def get_input_filename():

                dlg = ui.createFileDialog()
                dlg.title = "Open bez.dat File"
                dlg.filter = "Airfoil .dat files (*.dat);;All Files (*.*)"
                if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
                    return

                filename = dlg.filename
                return filename

            def get_name(filename):
                name = ((str(filename).split("/"))[-1].replace(".DAT", "")).replace(".dat", "")
                return name

            # onInputChange for click Button
            if cmdInput.id == B1_BUTTON_ID:

                filename = get_input_filename()
                name = get_name(filename)
                airfoildata = AirfoilC(filename, name)
                airfoildata.get_profile()
                top_coords = list(airfoildata.top_coords)
                bottom_coords = list(airfoildata.bottom_coords)
                ui.messageBox("Profil eingelesen!")

        except:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


class FoilCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs

            try:

                in2 = inputs.itemById(I0_VALUE_ID)
                in3 = inputs.itemById(C0_CHECKBOX_ID)
                in7 = inputs.itemById(D1_DROPDOWN_ID)
                in8 = inputs.itemById(D2_DROPDOWN_ID)
                in9 = inputs.itemById(C1_CHECKBOX_ID)
                in11 = inputs.itemById(C2_CHECKBOX_ID)
                in12 = inputs.itemById(I1_VALUE_ID)
                in13 = inputs.itemById(I2_VALUE_ID)

                entities_nose = []
                entities_tail = []

                if inputs.itemById(SE01_SELECTION_INPUT_ID).selection(0).isValid == True:
                    entities_nose.append(inputs.itemById(SE01_SELECTION_INPUT_ID).selection(0).entity)
                else:
                    ui.messageBox("Rail at leading edge not selected!")
                    # args.isValidResult = False
                if inputs.itemById(SE02_SELECTION_INPUT_ID).selection(0).isValid == True:
                    entities_tail.append(inputs.itemById(SE02_SELECTION_INPUT_ID).selection(0).entity)
                else:
                    ui.messageBox("Rail at trailing edge not selected!")
                    # args.isValidResult = False
                if inputs.itemById(SE02_SELECTION_INPUT_ID).selection(0).isValid == True:
                    pass
                else:
                    ui.messageBox("Plane not selected!")
                    # args.isValidResult = False

            except:
                if ui:
                    ui.messageBox("Failed:\n{}".format(traceback.format_exc()))

            foil = Foil()
            foil.Execute(
                in2.value,
                in3.value,
                entities_nose,
                entities_tail,
                inputs.itemById(SE04_SELECTION_INPUT_ID).selection(0).entity,
                in7.selectedItem.name,
                in8.selectedItem.name,
                in9.value,
                in11.value,
                in12.value,
                in13.value,
            )

        except:
            if ui:
                ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


class FoilCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            adsk.terminate()
        except:
            if ui:
                ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


class Foil:
    def Execute(
        self,
        gap,
        mirror,
        splinenose,
        splinetail,
        planesel,
        x_axis_c,
        y_axis_c,
        breakcurve,
        tangency,
        dicke,
        interpolationspunkte,
    ):

        global top_coords, bottom_coords
        coords_o = top_coords
        coords_u = bottom_coords

        if dicke !=1:
            airfoildatad = AirfoilD(
                    name, top_coords, bottom_coords, dicke, interpolationspunkte
                )
            airfoildatad.make_thick()
            coords_o = airfoildatad.top_coords
            coords_u = airfoildatad.bottom_coords


        sketchT = sketches.add(planesel)
        try:
            sketchEntities1 = sketchT.intersectWithSketchPlane(splinenose)
            sketchEntities2 = sketchT.intersectWithSketchPlane(splinetail)
        except:
            ui.messageBox("Rails do not intersect with the selected plane!")

        for pt in sketchEntities1:
            if pt.objectType == adsk.fusion.SketchPoint.classType():
                nosep = sketchT.project(pt)

        for pt in sketchEntities2:
            if pt.objectType == adsk.fusion.SketchPoint.classType():
                tailp = sketchT.project(pt)

        line_sehne = sketchT.sketchCurves.sketchLines.addByTwoPoints(nosep.item(0), tailp.item(0))
        line_sehne.isConstruction = True

        # collections for intersections
        circlecoll_two_circles = adsk.core.ObjectCollection.create()
        linecoll_centerline = adsk.core.ObjectCollection.create()
        linecoll_gapline1 = adsk.core.ObjectCollection.create()
        linecoll_gapline2 = adsk.core.ObjectCollection.create()

        # get a perpendicular line to rootline by intersections of two circles with the rootlinelength as radius
        circle1 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(
            line_sehne.startSketchPoint.geometry, line_sehne.length
        )
        circlecoll_two_circles.add(circle1)
        circle2 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(
            line_sehne.endSketchPoint.geometry, line_sehne.length
        )

        circle_intersections = circle2.intersections(circlecoll_two_circles)
        circle_instersection1 = circle_intersections[2][0]
        circle_instersection2 = circle_intersections[2][1]

        # perpendicular line crossing rootline in the midpoint
        lineytest = sketchT.sketchCurves.sketchLines.addByTwoPoints(circle_instersection1, circle_instersection2)
        linecoll_centerline.add(lineytest)

        line_intersections = line_sehne.intersections(linecoll_centerline)

        # get the midpoint to use as startpoint of a vector to endpoint of rootline. Will be used to get perpendicular lines in unknown coordinate system at the tail.
        midpt = line_intersections[2][0]
        trans_to_tail = midpt.vectorTo(line_sehne.endSketchPoint.geometry)

        point_for_tail1 = lineytest.startSketchPoint.geometry.copy()
        point_for_tail2 = lineytest.endSketchPoint.geometry.copy()

        point_for_tail1.translateBy(trans_to_tail)
        point_for_tail2.translateBy(trans_to_tail)

        perpendicular_line1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
            line_sehne.endSketchPoint.geometry, point_for_tail1
        )
        linecoll_gapline1.add(perpendicular_line1)

        perpendicular_line2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
            line_sehne.endSketchPoint.geometry, point_for_tail2
        )
        linecoll_gapline2.add(perpendicular_line2)

        # get points on the perpendicular lines at half the distance of the tail gap
        if gap != 0:
            circle3 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(
                line_sehne.endSketchPoint.geometry, 0.5 * gap
            )

            gapline1_endpoint = circle3.intersections(linecoll_gapline1)
            gapline2_endpoint = circle3.intersections(linecoll_gapline2)
            gapline1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                line_sehne.endSketchPoint.geometry, gapline1_endpoint[2][0]
            )
            gapline2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                line_sehne.endSketchPoint.geometry, gapline2_endpoint[2][0]
            )
            circle3.deleteMe()

        # delete curves that are not needed anymore
        lineytest.deleteMe()
        perpendicular_line1.deleteMe()
        perpendicular_line2.deleteMe()
        circle1.deleteMe()
        circle2.deleteMe()

        suf = "suf"

        if str(suf).isalpha() is False:
            ui.messageBox("suffix contains signs other than alphanum")
        else:
            pass

        param_list = []
        design.allParameters.count

        def createParam(design, name, value, units, comment):
            userValue = adsk.core.ValueInput.createByReal(value)
            newParam = design.userParameters.add(name, userValue, units, comment)
            _user_parameters[name] = newParam

        def create_uniform_suffix(suf):
            for i in range(design.allParameters.count - 1):
                temp = design.allParameters.item(i)
                param_list.append(temp.name)

            if len(param_list) != 0:
                param_string = "".join(str(e) for e in param_list)
                counter = 97

                if str(suf) in param_string:
                    suf = str(suf) + str(chr(counter))
                    counter += 1
                    if str(suf) in param_string:
                        while str(suf) in param_string:
                            if counter < 123:
                                temp = suf[:-1]
                                suf = temp + str(chr(counter))
                            else:
                                temp = suf[:-1]
                                suf = temp + str(chr(counter)) + str(counter)
                            counter += 1
            return suf

        suf = create_uniform_suffix(suf)

        dim = sketchT.sketchDimensions

        if gap != 0:

            gappointu = gapline1.endSketchPoint
            gappointo = gapline2.endSketchPoint

        if x_axis_c == "in flight direction":
            if y_axis_c == "green up":
                if mirror is False:
                    mirror = True
                else:
                    mirror = False
            elif y_axis_c == "green down":
                pass
            elif y_axis_c == "red down":
                if mirror is False:
                    mirror = True
                else:
                    mirror = False
            elif y_axis_c == "red up":
                pass

        elif x_axis_c == "against flight direction":
            if y_axis_c == "green down":
                if mirror is False:
                    mirror = True
                else:
                    mirror = False
            elif y_axis_c == "green up":
                pass
            elif y_axis_c == "red up":
                if mirror is False:
                    mirror = True
                else:
                    mirror = False
            elif y_axis_c == "red down":
                pass
        else:
            ui.messageBox("New case, please report behavior.")

        # incline lines to form triangles with root and halfgaps
        if gap != 0:
            # top line
            gaplineO = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint, gappointo)
            gaplineO.isConstruction = True
            rootlineO = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                line_sehne.startSketchPoint, gaplineO.endSketchPoint
            )
            rootlineO.isConstruction = True
            dim.addDistanceDimension(
                rootlineO.startSketchPoint, rootlineO.endSketchPoint, 0, adsk.core.Point3D.create(-1, 1, 0), False
            )
            rootlineO_length = dim[-1].parameter.value
            dim[-1].parameter.name = "rootO" + str(suf)

            # bottom line
            gaplineU = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint, gappointu)
            gaplineU.isConstruction = True
            rootlineU = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                line_sehne.startSketchPoint, gaplineU.endSketchPoint
            )
            rootlineU.isConstruction = True
            dim.addDistanceDimension(
                rootlineU.startSketchPoint, rootlineU.endSketchPoint, 0, adsk.core.Point3D.create(-1, 1, 0), False
            )
            rootlineO_length = dim[-1].parameter.value
            dim[-1].parameter.name = "rootU" + str(suf)
        else:
            rootlineO = line_sehne
            rootlineU = rootlineO

        # get airfoil data and create final sketch
        sketchT.name = name + "_" + str(dicke * 100) + "%"

        # points collection top / bottom
        pointsM_O = adsk.core.ObjectCollection.create()
        pointsM_U = adsk.core.ObjectCollection.create()
        pointsM_OU = adsk.core.ObjectCollection.create()

        # lines from start to endpoint to rotate to the inclines later
        lineM_rootO = sketchT.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(float(coords_o[-1][0]), float(coords_o[-1][1]), 0),
            adsk.core.Point3D.create(float(coords_o[0][0]), float(coords_o[0][1]), 0),
        )
        lineM_rootO.isConstruction = True
        dim.addDistanceDimension(
            lineM_rootO.startSketchPoint, lineM_rootO.endSketchPoint, 0, adsk.core.Point3D.create(0, 0, 0), True
        )
        dim[-1].parameter.name = "rootO_is" + str(suf)
        rootlineO_lenght_is = dim[-1].parameter.value

        lineM_rootU = sketchT.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(float(coords_u[-1][0]), float(coords_u[-1][1]), 0),
            adsk.core.Point3D.create(float(coords_u[0][0]), float(coords_u[0][1]), 0),
        )
        lineM_rootU.isConstruction = True
        dim.addDistanceDimension(
            lineM_rootU.startSketchPoint, lineM_rootU.endSketchPoint, 0, adsk.core.Point3D.create(0, 0, 0), True
        )
        dim[-1].parameter.name = "rootU_is" + str(suf)
        rootlineU_lenght_is = dim[-1].parameter.value

        createParam(design, "scaleO" + str(suf), 1, "mm", "scalefactor")
        _user_parameters["scaleO" + str(suf)].expressions = "rootO" + str(suf) + "mm/rootO_is" + str(suf)

        createParam(design, "scaleU" + str(suf), 1, "mm", "scalefactorU")
        _user_parameters["scaleU" + str(suf)].expressions = "rootU" + str(suf) + "mm/rootU_is" + str(suf)

        # scale Matrix
        if gap == 0:
            rootlineO_length = line_sehne.length
        else:
            pass

        scale_factorO = rootlineO_length / rootlineO_lenght_is
        scale_factorU = rootlineO_length / rootlineU_lenght_is

        scaleMatrix = adsk.core.Matrix3D.create()
        scaleMatrix.setCell(0, 0, scale_factorO)
        scaleMatrix.setCell(1, 1, scale_factorO)

        scaleMatrixU = adsk.core.Matrix3D.create()
        scaleMatrixU.setCell(0, 0, scale_factorU)
        scaleMatrixU.setCell(1, 1, scale_factorU)

        # translation Matrix to nose
        # transvector = adsk.core.Vector3D.create(noseN_array[0], noseN_array[1], 0.0)
        transvector = adsk.core.Vector3D.create(
            line_sehne.startSketchPoint.geometry.x, line_sehne.startSketchPoint.geometry.y, 0.0
        )
        translation = transvector

        # rootline vectors for rotation
        ar1o = rootlineO.startSketchPoint.geometry.asArray()
        ar2o = rootlineO.endSketchPoint.geometry.asArray()
        vector_rootlineO = adsk.core.Vector3D.create(
            -float(ar1o[0]) + float(ar2o[0]), -float(ar1o[1]) + float(ar2o[1]), 0
        )

        ar1u = rootlineU.startSketchPoint.geometry.asArray()
        ar2u = rootlineU.endSketchPoint.geometry.asArray()
        vector_rootlineU = adsk.core.Vector3D.create(
            -float(ar1u[0]) + float(ar2u[0]), -float(ar1u[1]) + float(ar2u[1]), 0
        )

        # create points to perform translations for endpoints of top and bottom coordinates to get vectors for rotation matrix
        pointv1 = adsk.core.Point3D.create(float(coords_o[-1][0]), float(coords_o[-1][1]), 0)
        pointv2 = adsk.core.Point3D.create(float(coords_o[0][0]), float(coords_o[0][1]), 0)
        pointv1.transformBy(scaleMatrix)
        pointv1.translateBy(translation)
        pointv2.transformBy(scaleMatrix)
        pointv2.translateBy(translation)
        vector_rot_origin_O = pointv1.vectorTo(pointv2)

        pointv1u = adsk.core.Point3D.create(float(coords_u[-1][0]), float(coords_u[-1][1]), 0)
        pointv2u = adsk.core.Point3D.create(float(coords_u[0][0]), float(coords_u[0][1]), 0)
        pointv1u.transformBy(scaleMatrixU)
        pointv1u.translateBy(translation)
        pointv2u.transformBy(scaleMatrixU)
        pointv2u.translateBy(translation)
        vector_rot_origin_U = pointv2u.vectorTo(pointv1u)

        rotationMatrixO = adsk.core.Matrix3D.create()
        rotationMatrixO.setToRotateTo(vector_rot_origin_O, vector_rootlineO)
        sketchPointM = sketchT.sketchPoints

        rotationMatrixU = adsk.core.Matrix3D.create()
        rotationMatrixU.setToRotateTo(vector_rot_origin_U, vector_rootlineU)
        sketchPointMu = sketchT.sketchPoints

        # rotation matrix for mirror
        noserot = line_sehne.startSketchPoint.geometry.asArray()
        tailrot = line_sehne.endSketchPoint.geometry.asArray()
        noserotp = adsk.core.Point3D.create(noserot[0], noserot[1], 0.0)
        tailrotp = adsk.core.Point3D.create(tailrot[0], tailrot[1], 0.0)
        rotvector = noserotp.vectorTo(tailrotp)

        mirror_rotMatrix = adsk.core.Matrix3D.create()
        mirror_rotMatrix.setToRotation(math.radians(180), rotvector, noserotp)

        # translate top points, rotation comes later
        for i in range(len(coords_o)):
            point = adsk.core.Point3D.create(float(coords_o[i][0]), float(coords_o[i][1]), 0)
            point.transformBy(scaleMatrix)
            point.transformBy(rotationMatrixO)
            point.translateBy(translation)
            if mirror is True:
                point.transformBy(mirror_rotMatrix)

            pointsM_O.add(point)
            pointsM_OU.add(point)
            sketchPointM.add(point)

        lineM_rootO.deleteMe()

        point_testrans2 = adsk.core.Point3D.create(float(coords_u[0][0]), float(coords_u[0][1]), 0)
        point_testrans2.transformBy(scaleMatrixU)
        point_testrans2.transformBy(rotationMatrixU)

        point_testrans2goal = adsk.core.Point3D.create(
            line_sehne.startSketchPoint.geometry.x, line_sehne.startSketchPoint.geometry.y, 0.0
        )

        transvector2 = point_testrans2.vectorTo(point_testrans2goal)
        translation2 = transvector2

        # translate bottom points
        for i in range(len(coords_u)):
            point = adsk.core.Point3D.create(float(coords_u[i][0]), float(coords_u[i][1]), 0)
            point.transformBy(scaleMatrixU)
            point.transformBy(rotationMatrixU)
            point.translateBy(translation2)
            if mirror is True:
                point.transformBy(mirror_rotMatrix)

            pointsM_U.add(point)
            pointsM_OU.add(point)
            if i > 0:
                sketchPointMu.add(point)

        lineM_rootU.deleteMe()

        counter = dim.count
        while counter > 0:
            n = counter - 1
            dim.item(n).deleteMe()
            counter -= 1

        # avoide dublette at nose
        for i in range(1, pointsM_OU.count - 2):
            if pointsM_OU.item(i).isEqualTo(pointsM_OU.item(i + 1)):
                pointsM_OU.removeByIndex(i)

        # one whole spline
        spline = sketchT.sketchCurves.sketchFittedSplines.add(pointsM_OU)
        if gap == 0:
            spline.isClosed = False

        gaplineO.deleteMe()
        gaplineU.deleteMe()
        rootlineO.deleteMe()
        rootlineU.deleteMe()

        handle = spline.getTangentHandle(spline.fitPoints.item(pointsM_O.count - 1))
        handle = spline.activateTangentHandle(spline.fitPoints.item(pointsM_O.count - 1))
        handle.isFixed = False

        if tangency == True:
            sketchT.geometricConstraints.addPerpendicular(handle, line_sehne)

        handle.isConstruction = True

        if gap == 0:
            spline.addFitPoint(0.99999)

        if breakcurve == True:
            line_sehne.isConstruction = False
            spline.breakCurve(pointsM_OU.item(pointsM_O.count - 2))
            line_sehne.isConstruction = True


class FoilExecutePreviewHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandEventArgs):
        # Code to react to the event.
        app.log("In MyExecutePreviewHandler event handler.")

        try:

            def get_gap_lines(halfgap):
                inputs = args.command.commandInputs
                command = args.firingEvent.sender
                inputs = command.commandInputs

                entities_nose = []
                entities_tail = []

                entities_nose.append(inputs.itemById(SE01_SELECTION_INPUT_ID).selection(0).entity)
                entities_tail.append(inputs.itemById(SE02_SELECTION_INPUT_ID).selection(0).entity)
                plane = inputs.itemById(SE04_SELECTION_INPUT_ID).selection(0).entity

                sketchT = sketches.add(plane)

                sketchEntities1 = sketchT.intersectWithSketchPlane(entities_nose)
                sketchEntities2 = sketchT.intersectWithSketchPlane(entities_tail)

                if len(sketchEntities1) == 0 or len(sketchEntities2) == 0:
                    ui.messageBox("At least one rail dos not intersect with the selected plane!")

                for pt in sketchEntities1:
                    if pt.objectType == adsk.fusion.SketchPoint.classType():
                        nosep = sketchT.project(pt)

                for pt in sketchEntities2:  # war nicht drin
                    if pt.objectType == adsk.fusion.SketchPoint.classType():
                        tailp = sketchT.project(pt)

                line_sehne = sketchT.sketchCurves.sketchLines.addByTwoPoints(nosep.item(0), tailp.item(0))
                line_sehne.isConstruction = True

                circlecoll_two_circles = adsk.core.ObjectCollection.create()
                linecoll_centerline = adsk.core.ObjectCollection.create()
                linecoll_gapline1 = adsk.core.ObjectCollection.create()
                linecoll_gapline2 = adsk.core.ObjectCollection.create()

                circle1 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(
                    line_sehne.startSketchPoint.geometry, line_sehne.length
                )
                circlecoll_two_circles.add(circle1)
                circle2 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(
                    line_sehne.endSketchPoint.geometry, line_sehne.length
                )

                circle_intersections = circle2.intersections(circlecoll_two_circles)
                circle_instersection1 = circle_intersections[2][0]
                circle_instersection2 = circle_intersections[2][1]

                lineytest = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                    circle_instersection1, circle_instersection2
                )
                linecoll_centerline.add(lineytest)

                line_intersections = line_sehne.intersections(linecoll_centerline)

                midpt = line_intersections[2][0]
                trans_to_tail = midpt.vectorTo(line_sehne.endSketchPoint.geometry)

                point_for_tail1 = lineytest.startSketchPoint.geometry.copy()
                point_for_tail2 = lineytest.endSketchPoint.geometry.copy()

                point_for_tail1.translateBy(trans_to_tail)
                point_for_tail2.translateBy(trans_to_tail)

                perpendicular_line1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                    line_sehne.endSketchPoint.geometry, point_for_tail1
                )
                linecoll_gapline1.add(perpendicular_line1)

                perpendicular_line2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                    line_sehne.endSketchPoint.geometry, point_for_tail2
                )
                linecoll_gapline2.add(perpendicular_line2)

                circle3 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(
                    line_sehne.endSketchPoint.geometry, halfgap
                )

                gapline1_endpoint = circle3.intersections(linecoll_gapline1)
                gapline2_endpoint = circle3.intersections(linecoll_gapline2)

                lineytest.deleteMe()
                perpendicular_line1.deleteMe()
                perpendicular_line2.deleteMe()
                circle1.deleteMe()
                circle2.deleteMe()
                circle3.deleteMe()

                gapline1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                    line_sehne.endSketchPoint.geometry, gapline1_endpoint[2][0]
                )
                gapline2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(
                    line_sehne.endSketchPoint.geometry, gapline2_endpoint[2][0]
                )

                return sketchT

            def show_coordinate_system(sketchT):

                # Koordinatensystem
                origin = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0))
                xPoint = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.4, 0, 0))
                xPoint2 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.475, 0, 0))
                xPoint3 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.625, 0, 0))
                xPoint4 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.7, 0, 0))
                xPoint5 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(1.1, 0, 0))
                yPoint = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0.4, 0))
                yPoint2 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0.475, 0))
                yPoint3 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0.625, 0))
                yPoint4 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0.7, 0))
                yPoint5 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 1.1, 0))
                zPoint = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0.4))
                zPoint2 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0.475))
                zPoint3 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0.625))
                zPoint4 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0.7))
                zPoint5 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 1.1))

                coordsystemGraphics = root.customGraphicsGroups.add()
                coordsystemGraphics.id = "coordsystem show"

                tempBRep = adsk.fusion.TemporaryBRepManager.get()
                radius = 0.015
                xCyl = tempBRep.createCylinderOrCone(origin, radius, xPoint, radius)
                xCy2 = tempBRep.createCylinderOrCone(xPoint2, radius, xPoint3, radius)
                xCy3 = tempBRep.createCylinderOrCone(xPoint4, radius, xPoint5, radius)
                yCyl = tempBRep.createCylinderOrCone(origin, radius, yPoint, radius)
                yCy2 = tempBRep.createCylinderOrCone(yPoint2, radius, yPoint3, radius)
                yCy3 = tempBRep.createCylinderOrCone(yPoint4, radius, yPoint5, radius)
                zCyl = tempBRep.createCylinderOrCone(origin, radius, zPoint, radius)
                zCy2 = tempBRep.createCylinderOrCone(zPoint2, radius, zPoint3, radius)
                zCy3 = tempBRep.createCylinderOrCone(zPoint4, radius, zPoint5, radius)

                red = adsk.core.Color.create(255, 0, 0, 255)
                green = adsk.core.Color.create(0, 255, 0, 255)
                blue = adsk.core.Color.create(0, 0, 255, 255)

                redColor = adsk.fusion.CustomGraphicsBasicMaterialColorEffect.create(red, red, red, red, 0, 1)
                greenColor = adsk.fusion.CustomGraphicsBasicMaterialColorEffect.create(
                    green, green, green, green, 0, 1
                )
                blueColor = adsk.fusion.CustomGraphicsBasicMaterialColorEffect.create(blue, blue, blue, blue, 0, 1)

                xCylGraphics = coordsystemGraphics.addBRepBody(xCyl)
                xCylGraphics.color = redColor
                xCylGraphics = coordsystemGraphics.addBRepBody(xCy2)
                xCylGraphics.color = redColor
                xCylGraphics = coordsystemGraphics.addBRepBody(xCy3)
                xCylGraphics.color = redColor

                yCylGraphics = coordsystemGraphics.addBRepBody(yCyl)
                yCylGraphics.color = greenColor
                yCylGraphics = coordsystemGraphics.addBRepBody(yCy2)
                yCylGraphics.color = greenColor
                yCylGraphics = coordsystemGraphics.addBRepBody(yCy3)
                yCylGraphics.color = greenColor

                zCylGraphics = coordsystemGraphics.addBRepBody(zCyl)
                zCylGraphics.color = blueColor
                zCylGraphics = coordsystemGraphics.addBRepBody(zCy2)
                zCylGraphics.color = blueColor
                zCylGraphics = coordsystemGraphics.addBRepBody(zCy3)
                zCylGraphics.color = blueColor

                viewScale = adsk.fusion.CustomGraphicsViewScale.create(100, origin)
                coordsystemGraphics.viewScale = viewScale

            sketchT = get_gap_lines(0.1)
            show_coordinate_system(sketchT)

        except:
            if ui:
                ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


class FoilCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandEventArgs):
        try:

            onExecutePreview = FoilExecutePreviewHandler()
            args.command.executePreview.add(onExecutePreview)
            _handlers.append(onExecutePreview)

            onExecute = FoilCommandExecuteHandler()
            args.command.execute.add(onExecute)
            _handlers.append(onExecute)

            onDestroy = FoilCommandDestroyHandler()
            args.command.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            onInputChanged = FoilCommandInputChangedHandler()
            args.command.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)

            inputs = args.command.commandInputs

            tabCmdInput1 = inputs.addTabCommandInput("tab_1", "Settings")
            tab1ChildInputs = tabCmdInput1.children

            groupCmdInput0 = tab1ChildInputs.addGroupCommandInput("group", "Auswahl der DAT-Datei:")
            groupCmdInput0.isExpanded = True
            groupCmdInput0.isEnabledCheckBoxDisplayed = False
            groupChildInputs0 = groupCmdInput0.children

            groupChildInputs0.addBoolValueInput(B1_BUTTON_ID, B1_BUTTON_NAME, False, "", True)

            groupCmdInput1 = tab1ChildInputs.addGroupCommandInput("group", "Auswahl der Splines und Projektionsebene:")
            groupCmdInput1.isExpanded = True
            groupCmdInput1.isEnabledCheckBoxDisplayed = False
            groupChildInputs1 = groupCmdInput1.children

            i1 = groupChildInputs1.addSelectionInput(
                SE01_SELECTION_INPUT_ID, SE01_SELECTION_INPUT_ID, "Schiene Nasenleiste"
            )
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchCurves)
            i2 = groupChildInputs1.addSelectionInput(
                SE02_SELECTION_INPUT_ID, SE02_SELECTION_INPUT_ID, "Schiene Endleiste"
            )
            i2.addSelectionFilter(adsk.core.SelectionCommandInput.SketchCurves)
            i5 = groupChildInputs1.addSelectionInput(
                SE04_SELECTION_INPUT_ID, SE04_SELECTION_INPUT_ID, "Projektionsebene"
            )
            i5.addSelectionFilter(adsk.core.SelectionCommandInput.ConstructionPlanes)

            groupCmdInput2 = tab1ChildInputs.addGroupCommandInput("group", "Ausrichtung:")
            groupCmdInput2.isExpanded = True
            groupCmdInput2.isEnabledCheckBoxDisplayed = False
            groupChildInputs2 = groupCmdInput2.children

            dropdownInput1 = groupChildInputs2.addDropDownCommandInput(
                D1_DROPDOWN_ID, D1_DROPDOWN_NAME, adsk.core.DropDownStyles.TextListDropDownStyle
            )
            dropdown_items1 = dropdownInput1.listItems
            dropdownInput1.maxVisibleItems = 6
            dropdownInput1.isFullWidth
            dropdown_items1.add("in flight direction", True, "")
            dropdown_items1.add("against flight direction", False, "")

            dropdownInput2 = groupChildInputs2.addDropDownCommandInput(
                D2_DROPDOWN_ID, D2_DROPDOWN_NAME, adsk.core.DropDownStyles.LabeledIconDropDownStyle
            )
            dropdown_items2 = dropdownInput2.listItems
            dropdownInput2.maxVisibleItems = 6
            dropdownInput2.isFullWidth
            dropdown_items2.add("red up", False, "resources/Redup")
            dropdown_items2.add("red down", False, "resources/Reddown")
            dropdown_items2.add("green up", True, "resources/Greenup")
            dropdown_items2.add("green down", False, "resources/Greendown")

            groupChildInputs2.addBoolValueInput(C0_CHECKBOX_ID, C0_CHECKBOX_ID, True, "", False)

            groupCmdInput3 = tab1ChildInputs.addGroupCommandInput("group", "Nasenleiste:")
            groupCmdInput3.isExpanded = True
            groupCmdInput3.isEnabledCheckBoxDisplayed = False
            groupChildInputs3 = groupCmdInput3.children

            groupChildInputs3.addBoolValueInput(C1_CHECKBOX_ID, C1_CHECKBOX_ID, True, "", False)
            groupChildInputs3.addBoolValueInput(C2_CHECKBOX_ID, C2_CHECKBOX_ID, True, "", True)

            groupCmdInput4 = tab1ChildInputs.addGroupCommandInput("group", "Endleiste:")
            groupCmdInput4.isExpanded = True
            groupCmdInput4.isEnabledCheckBoxDisplayed = False
            groupChildInputs4 = groupCmdInput4.children

            groupChildInputs4.addValueInput(I0_VALUE_ID, I0_VALUE_NAME, "mm", adsk.core.ValueInput.createByReal(0.05))

            groupCmdInput5 = tab1ChildInputs.addGroupCommandInput("group", "Profilaufdickung:")
            groupCmdInput5.isExpanded = False
            groupCmdInput5.isEnabledCheckBoxDisplayed = False
            groupChildInputs5 = groupCmdInput5.children

            groupChildInputs5.addValueInput(I1_VALUE_ID, I1_VALUE_NAME, "", adsk.core.ValueInput.createByReal(1.0))
            groupChildInputs5.addValueInput(I2_VALUE_ID, I2_VALUE_NAME, "", adsk.core.ValueInput.createByReal(100.0))

            tabCmdInput2 = inputs.addTabCommandInput("tab_2", "Help")
            tab2ChildInputs = tabCmdInput2.children

            inst_text1 = """ <p><strong>Instructions:</strong></p> \
                <p>Select rails for leading edge and trailing edge.\
                <p>Select a plane they intersect with.</p> \
                <p>When selections are made the axis of the coordinate system will be shown.</p> \
                <p>Provide information if horizontal axis points in or against flight direction.</p> \
                <p>Select the direction and color of the vertical axis, top means to the top of the airfoil.</p>
                <p>Select mirror if you want the airfoil to face down. Feature is left in case an airfoil does not flip in the right way.</p>
                
            """
            tab2ChildInputs.addTextBoxCommandInput("fullWidth_textBox", "", inst_text1, 12, True)

        except:
            if ui:
                ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


def run(context):
    try:

        cmdDef = ui.commandDefinitions.itemById(COMMAND_ID)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(COMMAND_ID, "Airfoil Import", "Airfoil Import")
        onCommandCreated = FoilCommandCreatedHandler()

        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        cmdDef.execute()
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


class AirfoilC:

    def __init__(self, filename, name):
        self.filename = filename
        self.name = name
        self.top_coords = []
        self.bottom_coords = []
        self.info = []
        self.profile = self.get_profile()

    def get_profile(self):

        with open(self.filename, encoding="utf-8") as a:
            text = a.read()

        muster = r"-?\d+\.\d{3,}"

        find_koord = re.compile(rf"^\s*({muster})\s*({muster})\s*$", flags=re.MULTILINE)

        abschnitte = []
        for abschnitt in text.split("\n\n"):
            koordinaten = find_koord.findall(abschnitt)
            if not koordinaten:
                continue

            abschnitte.append([(float(x), float(y)) for x, y in koordinaten])

        # selig format
        if len(abschnitte) == 1:
            self.profile = abschnitte[0]

        # lednicer format
        elif len(abschnitte) == 2 and abschnitte[0][0] == abschnitte[1][0]:
            # doppelte koordinate entfernen und einen Abschnitt rückwärts laufen
            temp = list(abschnitte[1][0])
            del temp[1]
            temp = list(reversed(temp))
            self.profile = temp + abschnitte[1]
        else:
            self.profile = []

        if self.profile[0][0] != 1 and self.profile[-1][0] == 1:
            self.profile.insert(0, (1, self.profile[0][1]))

        if self.profile[-1][0] != 1 and self.profile[0][0] == 1:
            self.profile.extend((1, self.profile[-1][1]))

        self.coords_split_move()

    def move(self):

        top = [
            (
                float(self.top_coords[i][0]) - float(self.bottom_coords[0][0]),
                float(self.top_coords[i][1]) - float(self.bottom_coords[0][1]),
            )
            for i in range(len(self.top_coords))
        ]
        bottom = [
            (
                float(self.bottom_coords[i][0]) - float(self.bottom_coords[0][0]),
                float(self.bottom_coords[i][1]) - float(self.bottom_coords[0][1]),
            )
            for i in range(len(self.bottom_coords))
        ]

        self.top_coords = top
        self.bottom_coords = bottom
        self.derotate()

    def derotate(self):

        alpha_top = self.get_alpha(self.top_coords[0][1], self.top_coords[0][0])
        alpha_bottom = self.get_alpha(self.bottom_coords[-1][1], self.bottom_coords[-1][0])
        top_new = []
        bottom_new = []
        for i in range(len(self.top_coords)):
            x, y = self.rotation(self.top_coords[i][0], self.top_coords[i][1], -alpha_top)
            top_new.append((x, y))

        for i in range(len(self.bottom_coords)):
            x, y = self.rotation(self.bottom_coords[i][0], self.bottom_coords[i][1], -alpha_bottom)
            bottom_new.append((x, y))

        self.top_coords = top_new
        self.bottom_coords = bottom_new
        self.normalize()

    def coords_split_move(self):
        x_values, y_values = map(list, zip(*self.profile))

        # check if x min is (0, 0) otherwise move to origin, derotate and normalize, if it is not sth like s3002
        nose_index = x_values.index(min(x_values))
        self.top_coords = self.profile[0 : nose_index + 1]
        self.bottom_coords = self.profile[nose_index:]

        if float(self.bottom_coords[0][0]) != 0 or float(self.bottom_coords[0][1]) != 0:
            if (
                float(self.bottom_coords[1][1]) < 0 and float(self.top_coords[-2][1]) > 0
            ):  # S3002 type no nose point given
                self.info.append("Das Profil besitzt keinen Punkt (0,0), keine vertikale Tangente an der Nase!")
                self.get_coords_nose()
            else:  # AG35 type with x min as Nosepoint
                self.info.append("Das Profil wird derotiert!")
                self.move()

    def normalize(self):
        if self.top_coords[0][0] < 0:
            factort = 1 / self.top_coords[0][0]
        elif self.top_coords[0][0] > 0:
            factort = self.top_coords[0][0]
        else:
            pass

        top_new = [(self.top_coords[i][0] * factort, self.top_coords[i][1]) for i in range(1, len(self.top_coords))]
        top_new.insert(0, (1, 0))

        if self.bottom_coords[-1][0] < 0:
            factorb = 1 / self.bottom_coords[-1][0]
        elif self.bottom_coords[-1][0] > 0:
            factorb = self.bottom_coords[-1][0]
        else:
            pass

        bottom_new = [
            (self.bottom_coords[i][0] * factorb, self.bottom_coords[i][1])
            for i in range(0, len(self.bottom_coords) - 1)
        ]
        bottom_new.append((1, 0))

        self.top_coords = top_new
        self.bottom_coords = bottom_new

    @staticmethod
    def rotation(x, y, alpha):
        x_new = x * math.cos(alpha) - y * math.sin(alpha)
        y_new = x * math.sin(alpha) + y * math.cos(alpha)

        return x_new, y_new

    @staticmethod
    def get_alpha(gegenkathete, ankathete):
        # avoid zero division
        if ankathete == 0:
            alpha = math.pi / 2 if gegenkathete > 0 else -math.pi / 2
        else:
            alpha = math.atan(gegenkathete / ankathete)

        return alpha

    def get_coords_nose(self):
        sketchNose = sketches.add(root.xYConstructionPlane)
        sketchNose.name = "GetNose"

        coordsO = self.top_coords
        coordsU = self.bottom_coords

        if coordsO[-1][0] == coordsU[0][0] and coordsO[-1][1] == coordsU[0][1]:
            del coordsU[0]

        coords = list(coordsO) + list(coordsU)
        coll = adsk.core.ObjectCollection.create()
        coll_line = adsk.core.ObjectCollection.create()

        for i in range(len(coords)):
            point = adsk.core.Point3D.create(coords[i][0], coords[i][1], 0)
            coll.add(point)

        spline = sketchNose.sketchCurves.sketchFittedSplines.add(coll)
        line = sketchNose.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(-0.3, 0, 0), adsk.core.Point3D.create(0.3, 0, 0)
        )
        coll_line.add(line)

        intersection = spline.intersections(coll_line)

        array = intersection[2][0].asArray()

        coordsU.insert(0, (array[0], 0))
        coordsO.append((array[0], 0))

        if array[0] < 0:
            s = abs(array[0])
        else:
            s = -array[0]

        t = 1 / (1 + s)  ### korrigieren in 1

        coordsUn = [((coordsU[i][0] + s) * t, coordsU[i][1], 0) for i in range(len(coordsU))]
        coordsOn = [((coordsO[i][0] + s) * t, coordsO[i][1], 0) for i in range(len(coordsO))]

        sketchNose.deleteMe()

        self.top_coords = coordsOn
        self.bottom_coords = coordsUn


class AirfoilD:
    def __init__(self, name, top_coords, bottom_coords, thickness, points):
        self.name = name
        self.top_coords = top_coords
        self.bottom_coords = bottom_coords
        self.thickness = thickness
        self.points = points

    def make_thick(self):

        def cos_verteilung(punkte: int, rootlength: float):
            x_values = []
            step = math.pi / (punkte - 1)

            for i in range(punkte):
                theta = i * step / 2
                x = 1 - math.cos(theta)
                x_values.append(x * rootlength)

            return x_values

        factor = self.thickness
        ipoints = self.points
        top = self.top_coords
        bottom = self.bottom_coords

        xt = [top[i][0] for i in range(len(top))]
        xb = list(reversed([bottom[i][0] for i in range(len(bottom))]))

        top2 = top
        del top2[-1]
        combined = list(top2) + list(bottom)

        sketchChamber = sketches.add(root.xYConstructionPlane)
        sketchChamber.name = "Interpolation"

        points = adsk.core.ObjectCollection.create()
        for i in range(len(combined)):
            point = adsk.core.Point3D.create(float(combined[i][0]), float(combined[i][1]), 0)
            points.add(point)

        if points.count % 2 != 0:
            breakpoint = int((points.count - 1) / 2) - 1
        else:
            breakpoint = int((points.count) / 2) - 1

        breakline = sketchChamber.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(0.2, 0, 0)
        )
        normal = sketchChamber.sketchCurves.sketchFittedSplines.add(points)
        normal.isClosed = False

        splines = normal.breakCurve(points.item(breakpoint))

        splines.item(1).addFitPoint(0.99999)
        sketchChamber.geometricConstraints.addCoincident(
            splines.item(1).endSketchPoint, splines.item(0).startSketchPoint
        )

        rootlength = 1

        x_verteilung = cos_verteilung(int(ipoints * 0.5), rootlength)

        O = []
        U = []

        for i in range(1, len(x_verteilung) - 1):
            collLines = adsk.core.ObjectCollection.create()
            pu = adsk.core.Point3D.create(float(x_verteilung[i]), -10, 0)
            po = adsk.core.Point3D.create(float(x_verteilung[i]), 10, 0)
            line = sketchChamber.sketchCurves.sketchLines.addByTwoPoints(pu, po)
            collLines.add(line)
            O.append(splines.item(0).intersections(collLines)[2][0].asArray())
            U.append(splines.item(1).intersections(collLines)[2][0].asArray())
            line.deleteMe()

        scaledO = [(O[i][0] / rootlength, O[i][1] / rootlength) for i in range(len(O) - 1)]
        scaledO.append((1, 0))
        scaledU = [(U[i][0] / rootlength, U[i][1] / rootlength) for i in range(len(U) - 1)]  # test negiert
        scaledU.append((1, 0))
        chamber = [(scaledO[i][0], (scaledO[i][1] + scaledU[i][1]) * 0.5, 0) for i in range(len(scaledO))]

        thickO = [
            (chamber[i][0], (factor * (scaledO[i][1] - chamber[i][1])) + chamber[i][1], 0) for i in range(len(chamber))
        ]
        thickU = [
            (chamber[i][0], (factor * (scaledU[i][1] - chamber[i][1])) + chamber[i][1], 0) for i in range(len(chamber))
        ]

        origin = [(0, 0)]
        chamber_line = [(0, 0, 0)] + chamber

        thicked = list(reversed(thickO)) + list(origin) + list(thickU)
        thickedO = list(reversed(thickO)) + list(origin)
        thickedU = list(thickU)

        self.top_coords = thickedO
        self.bottom_coords = thickedU

        sketchChamber.deleteMe()
