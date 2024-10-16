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
C2_CHECKBOX_ID = "Bei 0 mm manuell reparieren"
C3_CHECKBOX_ID = "Tangentenhantel vertikal"

_handlers = []
_user_parameters = {}

ui = None
app = adsk.core.Application.get()
if app:
    ui = app.userInterface

product = app.activeProduct
design = adsk.fusion.Design.cast(product)
root = design.rootComponent
sketches = root.sketches
planes = root.constructionPlanes


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
                in10 = inputs.itemById(C2_CHECKBOX_ID)
                in11 = inputs.itemById(C3_CHECKBOX_ID)

                entities_nose = []
                entities_tail = []           
                
                if inputs.itemById(SE01_SELECTION_INPUT_ID).selection(0).isValid == True:
                    entities_nose.append(inputs.itemById(SE01_SELECTION_INPUT_ID).selection(0).entity)
                else:
                    ui.messageBox("Rail at leading edge not selected!")
                    #args.isValidResult = False
                if inputs.itemById(SE02_SELECTION_INPUT_ID).selection(0).isValid == True:
                    entities_tail.append(inputs.itemById(SE02_SELECTION_INPUT_ID).selection(0).entity)
                else:
                    ui.messageBox("Rail at trailing edge not selected!")
                    #args.isValidResult = False
                if inputs.itemById(SE02_SELECTION_INPUT_ID).selection(0).isValid == True:
                    pass
                else:
                    ui.messageBox("Plane not selected!")
                    #args.isValidResult = False
               
            except:
                if ui:
                    ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
    
            foil = Foil()
            foil.Execute(in2.value, in3.value, entities_nose, entities_tail, inputs.itemById(SE04_SELECTION_INPUT_ID).selection(0).entity, in7.selectedItem.name, in8.selectedItem.name, in9.value, in10.value, in11.value)


        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))



class FoilCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class Foil:
    def Execute(self, gap, mirror, splinenose, splinetail, planesel, x_axis_c, y_axis_c, breakcurve, repairm, tangency):
            
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
        circle1 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(line_sehne.startSketchPoint.geometry, line_sehne.length)
        circlecoll_two_circles.add(circle1)
        circle2 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(line_sehne.endSketchPoint.geometry, line_sehne.length)
    
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

        perpendicular_line1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, point_for_tail1)
        linecoll_gapline1.add(perpendicular_line1)

        perpendicular_line2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, point_for_tail2)
        linecoll_gapline2.add(perpendicular_line2)
        
        # get points on the perpendicular lines at half the distance of the tail gap
        if gap != 0:
            circle3 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(line_sehne.endSketchPoint.geometry, 0.5 * gap)

            gapline1_endpoint = circle3.intersections(linecoll_gapline1)
            gapline2_endpoint = circle3.intersections(linecoll_gapline2)
            gapline1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, gapline1_endpoint[2][0])
            gapline2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, gapline2_endpoint[2][0])
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
            for i in range(design.allParameters.count -1):
                temp = design.allParameters.item(i)
                param_list.append(temp.name)
            
            if len(param_list) != 0:
                param_string = ''.join(str(e) for e in param_list)
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
                            counter +=1
            return suf
        
        suf = create_uniform_suffix(suf)

        sketchN = sketches.add(sketchT.referencePlane)
        #originN = sketchN.originPoint
        dimN = sketchN.sketchDimensions
        noseN_array = line_sehne.startSketchPoint.geometry.asArray()
        
        noseN = (sketchN.project(line_sehne.startSketchPoint)).item(0)
        tailN = (sketchN.project(line_sehne.endSketchPoint)).item(0)
        
        linexN = sketchN.sketchCurves.sketchLines.addByTwoPoints(noseN, tailN)
        linexN.isReference = False
        linexN.isConstruction = True

        # get airfoil coordinates
        airfoils = AirfoilC()
        coords_o, coords_u= airfoils.coords_split_move()
        
        if gap !=0:
            gappointu = (sketchN.project(gapline1.endSketchPoint)).item(0)
            gappointo = (sketchN.project(gapline2.endSketchPoint)).item(0)

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
            gaplineO = sketchN.sketchCurves.sketchLines.addByTwoPoints(linexN.endSketchPoint, gappointo)
            gaplineO.isConstruction = True
            rootlineO = sketchN.sketchCurves.sketchLines.addByTwoPoints(linexN.startSketchPoint, gaplineO.endSketchPoint)
            rootlineO.isConstruction = True
            dimN.addDistanceDimension(rootlineO.startSketchPoint, rootlineO.endSketchPoint, 0, adsk.core.Point3D.create(-1, 1, 0), False)
            rootlineO_length = dimN[-1].parameter.value
            dimN[-1].parameter.name = "rootO" + str(suf)
        
            # bottom line
            gaplineU = sketchN.sketchCurves.sketchLines.addByTwoPoints(linexN.endSketchPoint, gappointu)
            gaplineU.isConstruction = True
            rootlineU = sketchN.sketchCurves.sketchLines.addByTwoPoints(linexN.startSketchPoint, gaplineU.endSketchPoint)
            rootlineU.isConstruction = True
            dimN.addDistanceDimension(rootlineU.startSketchPoint, rootlineU.endSketchPoint, 0, adsk.core.Point3D.create(-1, 1, 0), False)
            rootlineO_length = dimN[-1].parameter.value
            dimN[-1].parameter.name = "rootU" + str(suf)
        else:
            rootlineO = linexN
            rootlineU = rootlineO
      

        # get airfoil data and create final sketch
        sketchM = sketches.add(sketchT.referencePlane)
        sketchM.name = airfoils.name
        dimM = sketchN.sketchDimensions
        
        # points collection top / bottom
        pointsM_O = adsk.core.ObjectCollection.create()
        pointsM_U = adsk.core.ObjectCollection.create()
        pointsM_OU = adsk.core.ObjectCollection.create()
        
        # lines from start to endpoint to rotate to the inclines later
        lineM_rootO = sketchN.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(float(coords_o[-1][0]), float(coords_o[-1][1]), 0), adsk.core.Point3D.create(float(coords_o[0][0]), float(coords_o[0][1]), 0))
        lineM_rootO.isConstruction = True
        dimM.addDistanceDimension(lineM_rootO.startSketchPoint, lineM_rootO.endSketchPoint, 0, adsk.core.Point3D.create(0, 0, 0), True)
        dimM[-1].parameter.name = "rootO_is" + str(suf)
        rootlineO_lenght_is = dimN[-1].parameter.value

        lineM_rootU = sketchN.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(float(coords_u[-1][0]), float(coords_u[-1][1]), 0), adsk.core.Point3D.create(float(coords_u[0][0]), float(coords_u[0][1]), 0))
        lineM_rootU.isConstruction = True
        dimM.addDistanceDimension(lineM_rootU.startSketchPoint, lineM_rootU.endSketchPoint, 0, adsk.core.Point3D.create(0, 0, 0), True)
        dimM[-1].parameter.name = "rootU_is" + str(suf)
        rootlineU_lenght_is = dimN[-1].parameter.value

        createParam(design, "scaleO" + str(suf), 1, "mm", "scalefactor")
        _user_parameters["scaleO" + str(suf)].expressions = "rootO" + str(suf) + "mm/rootO_is" + str(suf)

        createParam(design, "scaleU" + str(suf), 1, "mm", "scalefactorU")
        _user_parameters["scaleU" + str(suf)].expressions = "rootU" + str(suf) + "mm/rootU_is" + str(suf)
        
        
        # scale Matrix
        if gap == 0:
            rootlineO_length = linexN.length
        else:
            pass

        scale_factorO = rootlineO_length/rootlineO_lenght_is
        scale_factorU = rootlineO_length/rootlineU_lenght_is

        scaleMatrix = adsk.core.Matrix3D.create()
        scaleMatrix.setCell(0, 0, scale_factorO)
        scaleMatrix.setCell(1, 1, scale_factorO)

        scaleMatrixU = adsk.core.Matrix3D.create()
        scaleMatrixU.setCell(0, 0, scale_factorU)
        scaleMatrixU.setCell(1, 1, scale_factorU)

        # translation Matrix to nose
        transvector = adsk.core.Vector3D.create(noseN_array[0], noseN_array[1], 0.0)       
        translation = transvector
        
        # rootline vectors for rotation
        ar1o = rootlineO.startSketchPoint.geometry.asArray()
        ar2o = rootlineO.endSketchPoint.geometry.asArray()
        vector_rootlineO = adsk.core.Vector3D.create(-float(ar1o[0]) + float(ar2o[0]), -float(ar1o[1]) + float(ar2o[1]), 0)

        ar1u = rootlineU.startSketchPoint.geometry.asArray()
        ar2u = rootlineU.endSketchPoint.geometry.asArray()
        vector_rootlineU = adsk.core.Vector3D.create(-float(ar1u[0]) + float(ar2u[0]), -float(ar1u[1]) + float(ar2u[1]), 0)
        
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
        sketchPointM = sketchM.sketchPoints

        rotationMatrixU = adsk.core.Matrix3D.create()
        rotationMatrixU.setToRotateTo(vector_rot_origin_U, vector_rootlineU)
        sketchPointMu = sketchM.sketchPoints

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
        
        # use half spline to easy adress start and endpoints after rotation
        splineO = sketchM.sketchCurves.sketchFittedSplines.add(pointsM_O)  
        lineM_rootO = sketchM.sketchCurves.sketchLines.addByTwoPoints(splineO.startSketchPoint, splineO.endSketchPoint)
        lineM_rootO.isConstruction = True

        point_testrans2 = adsk.core.Point3D.create(float(coords_u[0][0]), float(coords_u[0][1]), 0)
        point_testrans2.transformBy(scaleMatrixU)
        point_testrans2.transformBy(rotationMatrixU)

        point_testrans2goal = adsk.core.Point3D.create(noseN_array[0], noseN_array[1], 0.0)

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
        
        splineU = sketchM.sketchCurves.sketchFittedSplines.add(pointsM_U)
        lineM_rootU = sketchM.sketchCurves.sketchLines.addByTwoPoints(splineU.startSketchPoint, splineU.endSketchPoint)
        lineM_rootU.isConstruction = True

        if gap != 0:
            sketchM.sketchCurves.sketchLines.addByTwoPoints(splineO.startSketchPoint, splineU.endSketchPoint)
        else:
            pass

        for item in sketchN.sketchPoints:
            item.deleteMe()

        lineM_rootO.startSketchPoint.deleteMe()
        lineM_rootO.endSketchPoint.deleteMe()
        lineM_rootU.startSketchPoint.deleteMe()
        lineM_rootU.endSketchPoint.deleteMe()

        lineM_rootO.deleteMe()
        lineM_rootU.deleteMe()
        sketchN.deleteMe()

        splineO.startSketchPoint.deleteMe()
        splineO.endSketchPoint.deleteMe()
        splineU.startSketchPoint.deleteMe()
  
        splineO.deleteMe()                 
        splineU.deleteMe()
        #sketchT.deleteMe()

        # avoide dublette at nose        
        for i in range(1, pointsM_OU.count - 2):
            if pointsM_OU.item(i).isEqualTo(pointsM_OU.item(i+1)):
                pointsM_OU.removeByIndex(i)

        # one whole spline
        spline = sketchM.sketchCurves.sketchFittedSplines.add(pointsM_OU)
        if gap == 0:
            spline.isClosed = False

        point1 = spline.fitPoints.item(pointsM_O.count -1)
        point2 = (sketchM.project(line_sehne.endSketchPoint)).item(0)
        linetest = sketchM.sketchCurves.sketchLines.addByTwoPoints(point1, point2)
        linetest.isFixed = True


        handle = spline.getTangentHandle(spline.fitPoints.item(pointsM_O.count -1))
        chandle = spline.getCurvatureHandle(spline.fitPoints.item(pointsM_O.count -1))
        
        handle = spline.activateTangentHandle(spline.fitPoints.item(pointsM_O.count -1))
        handle.isFixed = False

        if tangency == True:
            sketchM.geometricConstraints.addPerpendicular(handle, linetest)
        
        handle.isConstruction = True

        if gap == 0:
            if repairm == False:
                spline.addFitPoint(0.99999)
                sketchM.geometricConstraints.addCoincident(spline.endSketchPoint, linetest.endSketchPoint)
        
        if breakcurve == True:
            new_spline = spline.breakCurve(pointsM_OU.item(pointsM_O.count -2))
            new_spline0 = sketchM.sketchCurves.item(sketchM.sketchCurves.count -2)
            new_spline1 = sketchM.sketchCurves.item(sketchM.sketchCurves.count -1)

            sketchM.geometricConstraints.addCoincident(new_spline1.endSketchPoint, linetest.endSketchPoint)

        else:
            pass    
        
        linetest.isConstruction = True
        point2.deleteMe()
        sketchT.deleteMe()  
        

             



class FoilExecutePreviewHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args: adsk.core.CommandEventArgs):
        # Code to react to the event.
        app.log('In MyExecutePreviewHandler event handler.')

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

                for pt in sketchEntities2:   # war nicht drin
                    if pt.objectType == adsk.fusion.SketchPoint.classType():
                        tailp = sketchT.project(pt)

                line_sehne = sketchT.sketchCurves.sketchLines.addByTwoPoints(nosep.item(0), tailp.item(0))
                line_sehne.isConstruction = True
                
                circlecoll_two_circles = adsk.core.ObjectCollection.create()
                linecoll_centerline = adsk.core.ObjectCollection.create()
                linecoll_gapline1 = adsk.core.ObjectCollection.create()
                linecoll_gapline2 = adsk.core.ObjectCollection.create()

                circle1 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(line_sehne.startSketchPoint.geometry, line_sehne.length)
                circlecoll_two_circles.add(circle1)
                circle2 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(line_sehne.endSketchPoint.geometry, line_sehne.length)
            
                circle_intersections = circle2.intersections(circlecoll_two_circles)
                circle_instersection1 = circle_intersections[2][0]
                circle_instersection2 = circle_intersections[2][1]

                lineytest = sketchT.sketchCurves.sketchLines.addByTwoPoints(circle_instersection1, circle_instersection2)
                linecoll_centerline.add(lineytest)

                line_intersections = line_sehne.intersections(linecoll_centerline)

                midpt = line_intersections[2][0]
                trans_to_tail = midpt.vectorTo(line_sehne.endSketchPoint.geometry)

                point_for_tail1 = lineytest.startSketchPoint.geometry.copy()
                point_for_tail2 = lineytest.endSketchPoint.geometry.copy()
                
                point_for_tail1.translateBy(trans_to_tail)
                point_for_tail2.translateBy(trans_to_tail)

                perpendicular_line1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, point_for_tail1)
                linecoll_gapline1.add(perpendicular_line1)

                perpendicular_line2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, point_for_tail2)
                linecoll_gapline2.add(perpendicular_line2)
                
                circle3 = sketchT.sketchCurves.sketchCircles.addByCenterRadius(line_sehne.endSketchPoint.geometry, halfgap)

                gapline1_endpoint = circle3.intersections(linecoll_gapline1)
                gapline2_endpoint = circle3.intersections(linecoll_gapline2)
                
                lineytest.deleteMe()
                perpendicular_line1.deleteMe()
                perpendicular_line2.deleteMe()
                circle1.deleteMe()
                circle2.deleteMe()
                circle3.deleteMe()
                
                gapline1 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, gapline1_endpoint[2][0])
                gapline2 = sketchT.sketchCurves.sketchLines.addByTwoPoints(line_sehne.endSketchPoint.geometry, gapline2_endpoint[2][0])

                return sketchT


            def show_coordinate_system(sketchT):
                
                # Koordinatensystem
                origin = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0))
                xPoint = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.4, 0, 0))
                xPoint2 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.475, 0, 0))
                xPoint3 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.625, 0, 0))
                xPoint4 = sketchT.sketchToModelSpace(adsk.core.Point3D.create(0.7 ,0, 0))
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
                coordsystemGraphics.id = 'coordsystem show'

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

                red = adsk.core.Color.create(255,0 ,0 ,255)
                green = adsk.core.Color.create(0,255,0,255)
                blue = adsk.core.Color.create(0,0,255,255)


                redColor = adsk.fusion.CustomGraphicsBasicMaterialColorEffect.create(red, red, red, red, 0, 1)
                greenColor = adsk.fusion.CustomGraphicsBasicMaterialColorEffect.create(green, green, green, green, 0, 1)
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
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))




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
     

            inputs = args.command.commandInputs

            tabCmdInput1 = inputs.addTabCommandInput('tab_1', 'Settings')
            tab1ChildInputs = tabCmdInput1.children


            groupCmdInput = tab1ChildInputs.addGroupCommandInput('group', 'Auswahl der Splines und Projektionsebene:')
            groupCmdInput.isExpanded = True
            groupCmdInput.isEnabledCheckBoxDisplayed = False
            groupChildInputs = groupCmdInput.children

            i1 = groupChildInputs.addSelectionInput(SE01_SELECTION_INPUT_ID, SE01_SELECTION_INPUT_ID, "Schiene Nasenleiste")
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchCurves)
            i2 = groupChildInputs.addSelectionInput(SE02_SELECTION_INPUT_ID, SE02_SELECTION_INPUT_ID, "Schiene Endleiste")
            i2.addSelectionFilter(adsk.core.SelectionCommandInput.SketchCurves)
            i5 = groupChildInputs.addSelectionInput(SE04_SELECTION_INPUT_ID, SE04_SELECTION_INPUT_ID, "Projektionsebene")
            i5.addSelectionFilter(adsk.core.SelectionCommandInput.ConstructionPlanes)

            
            groupCmdInput2 = tab1ChildInputs.addGroupCommandInput('group', 'Ausrichtung:')
            groupCmdInput2.isExpanded = True
            groupCmdInput2.isEnabledCheckBoxDisplayed = False
            groupChildInputs2 = groupCmdInput2.children

            dropdownInput1 = groupChildInputs2.addDropDownCommandInput(D1_DROPDOWN_ID, D1_DROPDOWN_NAME, adsk.core.DropDownStyles.TextListDropDownStyle)
            dropdown_items1 = dropdownInput1.listItems
            dropdownInput1.maxVisibleItems = 6
            dropdownInput1.isFullWidth
            dropdown_items1.add("in flight direction", True, '')
            dropdown_items1.add("against flight direction", False, '')

            dropdownInput2 = groupChildInputs2.addDropDownCommandInput(D2_DROPDOWN_ID, D2_DROPDOWN_NAME, adsk.core.DropDownStyles.LabeledIconDropDownStyle)
            dropdown_items2 = dropdownInput2.listItems
            dropdownInput2.maxVisibleItems = 6
            dropdownInput2.isFullWidth
            dropdown_items2.add("red up", False, 'resources/Redup')
            dropdown_items2.add("red down", False, 'resources/Reddown')
            dropdown_items2.add("green up", True, 'resources/Greenup')
            dropdown_items2.add("green down", False, 'resources/Greendown')

            i3 = groupChildInputs2.addBoolValueInput(C0_CHECKBOX_ID, C0_CHECKBOX_ID, True, "", False)

            groupCmdInput3 = tab1ChildInputs.addGroupCommandInput('group', 'Nasenleiste:')
            groupCmdInput3.isExpanded = True
            groupCmdInput3.isEnabledCheckBoxDisplayed = False
            groupChildInputs3 = groupCmdInput3.children

            i4 = groupChildInputs3.addBoolValueInput(C1_CHECKBOX_ID, C1_CHECKBOX_ID, True, "", False)
            i7 = groupChildInputs3.addBoolValueInput(C3_CHECKBOX_ID, C3_CHECKBOX_ID, True, "", True)

            groupCmdInput4 = tab1ChildInputs.addGroupCommandInput('group', 'Endleiste:')
            groupCmdInput4.isExpanded = True
            groupCmdInput4.isEnabledCheckBoxDisplayed = False
            groupChildInputs4 = groupCmdInput4.children

            i2 = groupChildInputs4.addValueInput(I0_VALUE_ID, I0_VALUE_NAME, "mm", adsk.core.ValueInput.createByReal(0.05))

            i6 = groupChildInputs4.addBoolValueInput(C2_CHECKBOX_ID, C2_CHECKBOX_ID, True, "", False)

            tabCmdInput2 = inputs.addTabCommandInput('tab_2', 'Help')
            tab2ChildInputs = tabCmdInput2.children

           

            inst_text1 = """ <p><strong>Instructions:</strong></p> \
                <p>Select rails for leading edge and trailing edge.\
                <p>Select a plane they intersect with.</p> \
                <p>When selections are made the axis of the coordinate system will be shown.</p> \
                <p>Provide information if horizontal axis points in or against flight direction.</p> \
                <p>Select the direction and color of the vertical axis, top means to the top of the airfoil.</p>
                <p>Select mirror if you want the airfoil to face down. Feature is left in case an airfoil does not flip in the right way.</p>
                
            """
            tab2ChildInputs.addTextBoxCommandInput('fullWidth_textBox', '', inst_text1, 12, True)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:

        cmdDef = ui.commandDefinitions.itemById(COMMAND_ID)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(COMMAND_ID, 'Airfoil Import', 'Airfoil Import')
        onCommandCreated = FoilCommandCreatedHandler()

        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
        
        cmdDef.execute()
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class AirfoilC:

    def __init__(self):
        self.filename = self.get_input_filename()
        self.profile = self.get_profile()
        self.top_coords = []
        self.bottom_coords = []
        self.name = self.get_name()
        
    @classmethod
    def get_input_filename(cls):
        dlg = ui.createFileDialog()
        dlg.title = 'Open .dat File'
        dlg.filter = 'Airfoil .dat files (*.dat);;All Files (*.*)'
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return

        cls.filename = dlg.filename
        return cls.filename
    
    def get_name(self):
        self.name = ((str(self.filename).split("/"))[-1].replace(".DAT", "")).replace(".dat", "")
        return self.name
    
    @classmethod
    def get_profile(cls):
        
        with open(cls.filename, encoding="utf-8") as a:
            text = a.read()

        muster = r"-?\d+\.\d{3,}"

        find_koord = re.compile(fr"^\s*({muster})\s*({muster})\s*$", flags=re.MULTILINE)

        abschnitte = []
        for abschnitt in text.split("\n\n"):
            koordinaten = find_koord.findall(abschnitt)
            if not koordinaten:
                continue
    
            abschnitte.append([(float(x), float(y)) for x, y in koordinaten])

        # selig format
        if len(abschnitte) == 1:
            cls.profile = abschnitte[0]

        # lednicer format
        elif len(abschnitte) == 2 and abschnitte[0][0] == abschnitte[1][0]:
            # doppelte koordinate entfernen und einen Abschnitt rückwärts laufen
            temp = list(abschnitte[1][0])
            del temp[1]
            temp = list(reversed(temp))
            cls.profile = temp + abschnitte[1]
        else:
            cls.profile = []

        if cls.profile[0][0] != 1 and cls.profile[-1][0] == 1:
            cls.profile.insert(0, (1, cls.profile[0][1]))

        if cls.profile[-1][0] != 1 and cls.profile[0][0] == 1:
            cls.profile.extend((1, cls.profile[-1][1]))

        return cls.profile
        
    @classmethod
    def move(cls):
        
        top = [(float(cls.top_coords[i][0]) -float(cls.bottom_coords[0][0]), float(cls.top_coords[i][1]) -float(cls.bottom_coords[0][1])) for i in range(len(cls.top_coords))]
        bottom = [(float(cls.bottom_coords[i][0]) -float(cls.bottom_coords[-1][0]), float(cls.bottom_coords[i][1]) -float(cls.bottom_coords[-1][0])) for i in range(len(cls.bottom_coords))]
        cls.top_coords = top
        cls.bottom_coords = bottom
        return cls.top_coords, cls.bottom_coords
    
    @classmethod
    def coords_split_move(cls):
        x_values, y_values = map(list, zip(*cls.profile))

        # get min x to check if it is 0 and get min y to check if it's 0, move nose to 0.0
        nose_index = x_values.index(min(x_values))
        cls.top_coords = cls.profile[0:nose_index + 1]
        cls.bottom_coords = cls.profile[nose_index:]

        if float(cls.bottom_coords[-1][0]) != 0 or float(cls.bottom_coords[-1][1]) != 0:
            cls.move()

        return cls.top_coords, cls.bottom_coords
    
    def return_coords(self):
        a = self.top_coords
        b = self.bottom_coords
        
        return a, b

